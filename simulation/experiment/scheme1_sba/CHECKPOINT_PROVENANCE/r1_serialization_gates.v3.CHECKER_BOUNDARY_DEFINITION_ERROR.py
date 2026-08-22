# -*- coding: utf-8 -*-
# R-1a / R-1b / R-1c -- per-packet serialization gates.
#
# Replaces the original R-1
#     max sampled service_rate_bps <= C
# which was marked INVALID_GATE_PACKET_COMPLETION_QUANTIZATION: a fixed 5 us
# window holds 5.9637 packets of 1048 B, so a window that happens to complete 6
# whole packets measures 6288*8/5us = 10.0608 Gbps.  That is a sampling
# artefact, not a capacity violation, and the original gate could not tell the
# difference.
#
# These three gates read REAL per-packet events from the pure-observation
# recorder (time_ns, event, node_id, ifindex, link_id, packet_uid, size_bytes),
# where size_bytes comes straight from p->GetSize() in the callback.  No
# constant (1048 / 1064) is ever substituted for a measured size, and no
# percentage tolerance is used anywhere.
#
# Usage: python3 r1_serialization_gates.py <tx_csv> [capacity_bps] [label]
import csv
import os
import sys

TX = sys.argv[1] if len(sys.argv) > 1 else 'tx_trace/s3_rho090_tx.csv'
C = float(sys.argv[2]) if len(sys.argv) > 2 else 10e9
LABEL = sys.argv[3] if len(sys.argv) > 3 else TX

# ns-3 Time resolution is 1 ns by default in this build, so a single tick is
# 1 ns.  This is the ONLY tolerance permitted: it is the simulator's time
# quantum, not a percentage of anything.
TICK_NS = 1

HERE = os.path.dirname(os.path.abspath(__file__))
P = TX if os.path.isabs(TX) else os.path.join(HERE, TX)

gates = []
out = []


def gate(n, ok, d):
    gates.append((n, ok, d))


def rep(k, v):
    out.append((k, v))


if not os.path.exists(P):
    print('FATAL: %s missing' % P)
    sys.exit(2)

with open(P) as f:
    rows = list(csv.DictReader(f))

print('=' * 74)
print('R-1a/b/c PER-PACKET SERIALIZATION GATES -- %s' % LABEL)
print('=' * 74)
print('  source      : %s' % P)
print('  C           : %.4f Gbps' % (C / 1e9))
print('  time epsilon: %d ns (one simulator tick; NO percentage tolerance)'
      % TICK_NS)
print('')

if not rows:
    print('FATAL: trace is empty')
    sys.exit(2)

# ---------------------------------------------------------------------------
# assemble per-packet BEGIN/END pairs
# ---------------------------------------------------------------------------
beg = {}
end = {}
sizes = {}
links = set()
for r in rows:
    uid = r['packet_uid']
    t = int(r['time_ns'])
    sz = int(r['size_bytes'])
    links.add((r['node_id'], r['ifindex'], r['link_id']))
    if r['event'] == 'TX_BEGIN':
        beg.setdefault(uid, []).append((t, sz))
    elif r['event'] == 'TX_END':
        end.setdefault(uid, []).append((t, sz))
    sizes.setdefault(uid, set()).add(sz)

rep('rows', len(rows))
rep('link identity (node,if,link)', sorted(links))
rep('distinct packet_uid', len(set(list(beg.keys()) + list(end.keys()))))

# ---------------------------------------------------------------------------
# R-1a: physical serialization
# ---------------------------------------------------------------------------
dup_b = [u for u, v in beg.items() if len(v) != 1]
dup_e = [u for u, v in end.items() if len(v) != 1]
unmatched_b = [u for u in beg if u not in end]
unmatched_e = [u for u in end if u not in beg]

# A packet_uid can be reused by ns-3 across the run; treat a uid with exactly
# one BEGIN and one END as a clean pair and report reuse explicitly.
gate('R-1a.1 exactly one TX_BEGIN and one TX_END per packet_uid',
     len(dup_b) == 0 and len(dup_e) == 0,
     'duplicate BEGIN=%d duplicate END=%d' % (len(dup_b), len(dup_e)))
gate('R-1a.2 zero unmatched BEGIN / END',
     len(unmatched_b) == 0 and len(unmatched_e) == 0,
     'unmatched BEGIN=%d unmatched END=%d'
     % (len(unmatched_b), len(unmatched_e)))

pairs = []
for u in beg:
    if u in end and len(beg[u]) == 1 and len(end[u]) == 1:
        b, sz = beg[u][0]
        e, _ = end[u][0]
        pairs.append((b, e, sz, u))
pairs.sort()
rep('clean BEGIN/END pairs', len(pairs))

neg = [p for p in pairs if p[1] < p[0]]
gate('R-1a.3 TX_END >= TX_BEGIN for every packet',
     len(neg) == 0, '%d packets with END < BEGIN' % len(neg))

# duration must equal the device's own serialization time for that size
bad_dur = []
for b, e, sz, u in pairs:
    expect = int(round(sz * 8.0 / C * 1e9))     # ns, from the REAL size
    if abs((e - b) - expect) > TICK_NS:
        bad_dur.append((u, sz, e - b, expect))
gate('R-1a.4 duration == size_bytes*8/C for every packet (+/- 1 tick)',
     len(bad_dur) == 0,
     '%d packets deviate; first: %s' % (len(bad_dur), bad_dur[:1]))

# adjacency and overlap on the same link
overlaps = []
bad_adj = []
for i in range(1, len(pairs)):
    pb, pe, psz, pu = pairs[i - 1]
    cb, ce, csz, cu = pairs[i]
    if cb + TICK_NS < pe:
        overlaps.append((pu, pb, pe, cu, cb, ce))
    if cb < pe - TICK_NS:
        bad_adj.append((pu, pe, cu, cb))
gate('R-1a.5 TX_BEGIN never earlier than the previous TX_END',
     len(bad_adj) == 0,
     '%d violations; first: %s' % (len(bad_adj), bad_adj[:1]))
gate('R-1a.6 zero overlapping serialization intervals on the link',
     len(overlaps) == 0,
     '%d overlaps; first: %s' % (len(overlaps), overlaps[:1]))

if pairs:
    gaps = [pairs[i][0] - pairs[i - 1][1] for i in range(1, len(pairs))]
    rep('min inter-packet gap (BEGIN_i - END_{i-1})', '%d ns' % min(gaps))
    rep('max inter-packet gap', '%d ns' % max(gaps))
    rep('packet size histogram',
        sorted(set(p[2] for p in pairs))[:8])
    rep('first TX_BEGIN', '%d ns' % pairs[0][0])
    rep('last TX_END', '%d ns' % max(p[1] for p in pairs))

# ---------------------------------------------------------------------------
# R-1b: packet-aware window service curve
# ---------------------------------------------------------------------------
# served_bytes(t0,t1) <= C*(t1-t0)/8 + Lmax, where Lmax is the largest REAL
# size_bytes among the packets counted in that window.
print('')
print('--- R-1b: packet-aware window service curve ---')
print('  %-9s %14s %14s %8s %10s %7s  %s'
      % ('window', 'max_served_B', 'C*w/8_B', 'Lmax_B', 'excess_B', 'pkts',
         'worst window [t0,t1] ns'))
for w_us in (5, 50, 500):
    w_ns = w_us * 1000
    budget = C * w_ns / 1e9 / 8.0
    worst = None
    # A packet is attributed to the window in which it FINISHES, which is what
    # a fixed-window byte counter observes.  Lmax is taken from those packets.
    #
    # Implementation note: bucketed in ONE pass rather than rescanning `pairs`
    # per window.  The quantities computed are byte-for-byte the same
    # (served = sum of size_bytes finishing in the window, Lmax = max of those
    # size_bytes, excess = max(0, served - C*w/8)); only the loop order differs.
    # The naive form was 1.6e5 pairs x 3.1e4 windows = 5.0e9 operations.
    if pairs:
        t_lo = min(p[0] for p in pairs)
        acc = {}
        for b, e, sz, u in pairs:
            k = (e - t_lo) // w_ns
            a = acc.get(k)
            if a is None:
                acc[k] = [sz, sz, 1]
            else:
                a[0] += sz
                if sz > a[1]:
                    a[1] = sz
                a[2] += 1
        for k in sorted(acc):
            served, lmax, npk = acc[k]
            exc = max(0.0, served - budget)
            if worst is None or served > worst[0]:
                worst = (served, lmax, exc, npk,
                         t_lo + k * w_ns, t_lo + (k + 1) * w_ns)
    if worst:
        served, lmax, exc, npk, t0, t1 = worst
        ok = exc <= lmax
        print('  %-9s %14.0f %14.2f %8d %10.2f %7d  [%d, %d]'
              % ('%dus' % w_us, served, budget, lmax, exc, npk, t0, t1))
        gate('R-1b.%dus served <= C*w/8 + Lmax (Lmax from real p->GetSize())'
             % w_us, ok,
             'excess %.2f B <= Lmax %d B' % (exc, lmax))
        if t0 is not None:
            f = None
            for p in pairs:
                if t0 <= p[1] < t1 and (f is None or p < f):
                    f = p
            if f:
                rep('%dus worst window first pkt' % w_us,
                    'uid=%s tx_start=%d tx_finish=%d size=%d'
                    % (f[3], f[0], f[1], f[2]))

# ---------------------------------------------------------------------------
# R-1c: per-busy-period capacity
# ---------------------------------------------------------------------------
# Split into contiguous busy periods (gap > 0 ends a period), then check each.
print('')
print('--- R-1c: contiguous busy periods ---')
periods = []
if pairs:
    cur = [pairs[0]]
    for i in range(1, len(pairs)):
        if pairs[i][0] > cur[-1][1] + TICK_NS:
            periods.append(cur)
            cur = [pairs[i]]
        else:
            cur.append(pairs[i])
    periods.append(cur)

bad_bp = []
worst_bp = None
for pp in periods:
    bits = sum(p[2] for p in pp) * 8.0
    span_ns = pp[-1][1] - pp[0][0]
    if span_ns <= 0:
        continue
    rate = bits / (span_ns / 1e9)
    # allow exactly one tick of span slack, no percentage
    budget_bits = C * (span_ns + TICK_NS) / 1e9
    if bits > budget_bits:
        bad_bp.append((pp[0][0], pp[-1][1], len(pp), rate))
    if worst_bp is None or rate > worst_bp[3]:
        worst_bp = (pp[0][0], pp[-1][1], len(pp), rate)
rep('busy periods', len(periods))
if worst_bp:
    rep('worst busy period',
        '[%d, %d] %d pkts rate=%.6f Gbps'
        % (worst_bp[0], worst_bp[1], worst_bp[2], worst_bp[3] / 1e9))
gate('R-1c.1 every busy period: sum(size*8) <= C*span (+1 tick)',
     len(bad_bp) == 0,
     '%d busy periods exceed C; first: %s' % (len(bad_bp), bad_bp[:1]))

if pairs:
    tot_bits = sum(p[2] for p in pairs) * 8.0
    span = max(p[1] for p in pairs) - min(p[0] for p in pairs)
    lt = tot_bits / (span / 1e9) if span > 0 else 0.0
    rep('evaluation span', '%d ns' % span)
    rep('long-run average wire service rate', '%.6f Gbps' % (lt / 1e9))
    gate('R-1c.2 long-run average over the evaluation span <= C',
         lt <= C * (1.0 + 1.0 / max(span, 1)),
         '%.6f Gbps <= %.4f Gbps' % (lt / 1e9, C / 1e9))

# ---------------------------------------------------------------------------
print('')
print('--- measured ---')
for k, v in out:
    print('  %-40s %s' % (k, v))
print('')
print('--- gates ---')
fail = 0
for n, ok, d in gates:
    print('  [%s] %-58s %s' % ('PASS' if ok else 'FAIL', n, d))
    if not ok:
        fail += 1
print('')
print('  %d/%d gates passed' % (len(gates) - fail, len(gates)))
if fail:
    print('')
    print('  If an OVERLAP or duration failure appears, this is a real link or')
    print('  recorder-attachment error and must NOT be explained away as')
    print('  window quantization.  Stop and retain the full trace.')
sys.exit(1 if fail else 0)
