# -*- coding: utf-8 -*-
# R-1a / R-1b / R-1c, v4 -- boundary definitions corrected.
#
# Supersedes r1_serialization_gates.py (v3), retained as
# r1_serialization_gates.v3.CHECKER_BOUNDARY_DEFINITION_ERROR.py.  v3 failed two
# gates for reasons that were defects in the CHECKER, not in the controller, the
# link or the recorder:
#   R-1a.2  the trace's first row is a TX_END for a packet that began
#           serializing before the guard band opened -> 1 unmatched END.
#   R-1c.1  busy-period span was measured first TX_BEGIN -> last TX_END, which
#           systematically omits the leading packet's serialization time
#           (274 x 1048 B needs 229,721.6 ns; span measured 229,612 ns).
#
# v4 changes ONLY the boundary bookkeeping:
#   * the trace is split into leading guard / core / trailing guard;
#   * at most ONE unmatched END in the leading guard and ONE unmatched BEGIN in
#     the trailing guard are accepted, and only there, as BOUNDARY_CLIPPED;
#   * core must have zero unmatched events;
#   * busy periods are built ONLY from complete pairs inside core;
#   * R-1c compares work_ns = sum(tx_end - tx_begin) against span_ns, with NO
#     "span + first_packet_duration" compensation;
#   * a cross-check ties work_ns to sum(size*8/C) within one tick per packet;
#   * boundary-clipped packets enter neither numerator nor denominator.
#
# size_bytes always comes from the recorder's p->GetSize().  No 1048/1064
# constant is substituted, and no percentage tolerance exists anywhere: the only
# slack is TICK_NS, the simulator's own time quantum.
#
# Usage: python3 r1_gates_v4.py <tx_csv> <capacity_bps> <core_start_ns>
#                              <core_end_ns> [label]
import csv
import os
import sys

TICK_NS = 1          # ns-3 Time resolution in this build; the ONLY tolerance

gates = []
out = []


def gate(n, ok, d):
    gates.append((n, ok, d))


def rep(k, v):
    out.append((k, v))


def load(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def analyse(rows, C, core_lo, core_hi, label, verbose=True):
    """Returns (gates, report) for one trace. Pure; no globals mutated."""
    global gates, out
    gates = []
    out = []

    beg = {}
    end = {}
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

    rep('rows', len(rows))
    rep('link identity (node,if,link)', sorted(links))
    rep('core evaluation interval', '[%d, %d] ns' % (core_lo, core_hi))

    # ---- multiplicity: every uid at most one BEGIN and one END -------------
    dup_b = [u for u, v in beg.items() if len(v) != 1]
    dup_e = [u for u, v in end.items() if len(v) != 1]
    gate('R-1a.1 every packet_uid has at most one TX_BEGIN and one TX_END',
         len(dup_b) == 0 and len(dup_e) == 0,
         'duplicate BEGIN=%d duplicate END=%d' % (len(dup_b), len(dup_e)))

    # ---- three-zone unmatched accounting ----------------------------------
    # An unmatched END is only acceptable in the LEADING guard (its BEGIN
    # predates the trace).  An unmatched BEGIN is only acceptable in the
    # TRAILING guard (its END postdates the trace).
    unmatched_end = [(v[0][0], u) for u, v in end.items() if u not in beg]
    unmatched_beg = [(v[0][0], u) for u, v in beg.items() if u not in end]

    lead_end = [x for x in unmatched_end if x[0] < core_lo]
    core_end = [x for x in unmatched_end if core_lo <= x[0] <= core_hi]
    trail_end = [x for x in unmatched_end if x[0] > core_hi]
    lead_beg = [x for x in unmatched_beg if x[0] < core_lo]
    core_beg = [x for x in unmatched_beg if core_lo <= x[0] <= core_hi]
    trail_beg = [x for x in unmatched_beg if x[0] > core_hi]

    rep('unmatched END  lead/core/trail',
        '%d / %d / %d' % (len(lead_end), len(core_end), len(trail_end)))
    rep('unmatched BEGIN lead/core/trail',
        '%d / %d / %d' % (len(lead_beg), len(core_beg), len(trail_beg)))
    if lead_end:
        rep('BOUNDARY_CLIPPED_PACKET (leading END)',
            'uid=%s t=%d' % (lead_end[0][1], lead_end[0][0]))
    if trail_beg:
        rep('BOUNDARY_CLIPPED_PACKET (trailing BEGIN)',
            'uid=%s t=%d' % (trail_beg[0][1], trail_beg[0][0]))

    gate('R-1a.2a core interval has zero unmatched BEGIN and zero unmatched END',
         len(core_end) == 0 and len(core_beg) == 0,
         'core unmatched END=%d BEGIN=%d' % (len(core_end), len(core_beg)))
    gate('R-1a.2b leading guard has at most 1 unmatched END (and no BEGIN)',
         len(lead_end) <= 1 and len(lead_beg) == 0,
         'leading unmatched END=%d BEGIN=%d' % (len(lead_end), len(lead_beg)))
    gate('R-1a.2c trailing guard has at most 1 unmatched BEGIN (and no END)',
         len(trail_beg) <= 1 and len(trail_end) == 0,
         'trailing unmatched BEGIN=%d END=%d'
         % (len(trail_beg), len(trail_end)))

    # ---- complete pairs; core-only subset for capacity accounting ---------
    pairs = []
    for u in beg:
        if u in end and len(beg[u]) == 1 and len(end[u]) == 1:
            b, sz = beg[u][0]
            e, _ = end[u][0]
            pairs.append((b, e, sz, u))
    pairs.sort()
    # A packet counts toward core work only if it is ENTIRELY inside core.
    core = [p for p in pairs if p[0] >= core_lo and p[1] <= core_hi]
    clipped = len(pairs) - len(core)
    rep('complete pairs (all zones)', len(pairs))
    rep('complete pairs fully inside core', len(core))
    rep('pairs excluded as boundary/guard', clipped)

    gate('R-1a.3 TX_END >= TX_BEGIN for every complete pair',
         all(p[1] >= p[0] for p in pairs),
         '%d pairs with END < BEGIN' % sum(1 for p in pairs if p[1] < p[0]))

    bad_dur = []
    for b, e, sz, u in core:
        expect = int(round(sz * 8.0 / C * 1e9))
        if abs((e - b) - expect) > TICK_NS:
            bad_dur.append((u, sz, e - b, expect))
    gate('R-1a.4 duration == size_bytes*8/C for every core packet (+/-1 tick)',
         len(bad_dur) == 0,
         '%d deviate; first: %s' % (len(bad_dur), bad_dur[:1]))

    bad_adj = []
    overlaps = []
    for i in range(1, len(core)):
        pb, pe, psz, pu = core[i - 1]
        cb, ce, csz, cu = core[i]
        if cb < pe - TICK_NS:
            bad_adj.append((pu, pe, cu, cb))
        if cb + TICK_NS < pe:
            overlaps.append((pu, pb, pe, cu, cb, ce))
    gate('R-1a.5 TX_BEGIN never earlier than the previous TX_END (core)',
         len(bad_adj) == 0,
         '%d violations; first: %s' % (len(bad_adj), bad_adj[:1]))
    gate('R-1a.6 zero overlapping serialization intervals (core)',
         len(overlaps) == 0,
         '%d overlaps; first: %s' % (len(overlaps), overlaps[:1]))

    if core:
        gaps = [core[i][0] - core[i - 1][1] for i in range(1, len(core))]
        if gaps:
            rep('min inter-packet gap (core)', '%d ns' % min(gaps))
            rep('max inter-packet gap (core)', '%d ns' % max(gaps))
        rep('core packet sizes observed', sorted(set(p[2] for p in core))[:8])
        rep('core first TX_BEGIN / last TX_END',
            '%d / %d ns' % (core[0][0], max(p[1] for p in core)))

    # ---- R-1b: packet-aware window service curve (core packets only) -----
    if verbose:
        print('')
        print('--- R-1b: packet-aware window service curve (core only) ---')
        print('  %-8s %13s %13s %7s %10s %6s  %s'
              % ('window', 'max_served_B', 'C*w/8_B', 'Lmax_B', 'excess_B',
                 'pkts', 'worst window [t0,t1] ns'))
    for w_us in (5, 50, 500):
        w_ns = w_us * 1000
        budget = C * w_ns / 1e9 / 8.0
        worst = None
        if core:
            t_lo = core[0][0]
            acc = {}
            for b, e, sz, u in core:
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
            if verbose:
                print('  %-8s %13.0f %13.2f %7d %10.2f %6d  [%d, %d]'
                      % ('%dus' % w_us, served, budget, lmax, exc, npk, t0, t1))
            gate('R-1b.%dus served <= C*w/8 + Lmax (Lmax from real GetSize())'
                 % w_us, exc <= lmax,
                 'excess %.2f B <= Lmax %d B' % (exc, lmax))
            f = None
            for p in core:
                if t0 <= p[1] < t1 and (f is None or p < f):
                    f = p
            if f:
                rep('%dus worst window first pkt' % w_us,
                    'uid=%s tx_start=%d tx_finish=%d size=%d'
                    % (f[3], f[0], f[1], f[2]))

    # ---- R-1c: busy periods from CORE complete pairs only -----------------
    # work_ns = sum(tx_end - tx_begin); span_ns = last_end - first_begin.
    # No compensation term.  work <= span + one tick.
    periods = []
    if core:
        cur = [core[0]]
        for i in range(1, len(core)):
            if core[i][0] > cur[-1][1] + TICK_NS:
                periods.append(cur)
                cur = [core[i]]
            else:
                cur.append(core[i])
        periods.append(cur)

    bad_bp = []
    worst_bp = None
    bad_xcheck = []
    for pp in periods:
        work_ns = sum(p[1] - p[0] for p in pp)
        span_ns = pp[-1][1] - pp[0][0]
        if work_ns > span_ns + TICK_NS:
            bad_bp.append((pp[0][0], pp[-1][1], len(pp), work_ns, span_ns))
        util = float(work_ns) / span_ns if span_ns > 0 else 0.0
        if worst_bp is None or util > worst_bp[3]:
            worst_bp = (pp[0][0], pp[-1][1], len(pp), util, work_ns, span_ns)
        # cross-check: measured work vs the DataRate serialization time
        expect_ns = sum(p[2] * 8.0 / C * 1e9 for p in pp)
        if abs(work_ns - expect_ns) > len(pp) * TICK_NS:
            bad_xcheck.append((pp[0][0], len(pp), work_ns, expect_ns))

    rep('busy periods (core)', len(periods))
    if worst_bp:
        rep('worst busy period (by utilisation)',
            '[%d, %d] %d pkts work=%d ns span=%d ns util=%.6f'
            % (worst_bp[0], worst_bp[1], worst_bp[2], worst_bp[4],
               worst_bp[5], worst_bp[3]))
    gate('R-1c.1 every busy period: work_ns <= span_ns + 1 tick',
         len(bad_bp) == 0,
         '%d periods violate; first: %s' % (len(bad_bp), bad_bp[:1]))
    gate('R-1c.1x cross-check |work_ns - sum(size*8/C)| <= npkt * 1 tick',
         len(bad_xcheck) == 0,
         '%d periods deviate; first: %s' % (len(bad_xcheck), bad_xcheck[:1]))

    if core:
        tot_bits = sum(p[2] for p in core) * 8.0
        span = max(p[1] for p in core) - core[0][0]
        lt = tot_bits / (span / 1e9) if span > 0 else 0.0
        rep('core evaluation span', '%d ns' % span)
        rep('long-run average wire service rate', '%.6f Gbps' % (lt / 1e9))
        gate('R-1c.2 long-run average over the core span <= C',
             lt <= C, '%.6f Gbps <= %.4f Gbps' % (lt / 1e9, C / 1e9))

    return gates, out


def emit(label, C, gates_, out_):
    print('=' * 74)
    print('R-1a/b/c v4 -- %s' % label)
    print('=' * 74)
    print('  C            : %.4f Gbps' % (C / 1e9))
    print('  time epsilon : %d ns (one simulator tick; NO percentage tolerance)'
          % TICK_NS)
    print('')
    print('--- measured ---')
    for k, v in out_:
        print('  %-42s %s' % (k, v))
    print('')
    print('--- gates ---')
    fail = 0
    for n, ok, d in gates_:
        print('  [%s] %-60s %s' % ('PASS' if ok else 'FAIL', n, d))
        if not ok:
            fail += 1
    print('')
    print('  %d/%d gates passed' % (len(gates_) - fail, len(gates_)))
    return fail


if __name__ == '__main__':
    if len(sys.argv) < 5:
        print('usage: r1_gates_v4.py <tx_csv> <C_bps> <core_lo_ns> '
              '<core_hi_ns> [label]')
        sys.exit(2)
    HERE = os.path.dirname(os.path.abspath(__file__))
    tx = sys.argv[1]
    P = tx if os.path.isabs(tx) else os.path.join(HERE, tx)
    C = float(sys.argv[2])
    lo = int(sys.argv[3])
    hi = int(sys.argv[4])
    lab = sys.argv[5] if len(sys.argv) > 5 else tx
    if not os.path.exists(P):
        print('FATAL: %s missing' % P)
        sys.exit(2)
    g, o = analyse(load(P), C, lo, hi, lab)
    fail = emit(lab, C, g, o)
    if fail:
        print('')
        print('  If an OVERLAP or duration failure appears, this is a real link')
        print('  or recorder error and must NOT be explained away as window')
        print('  quantization.  Stop and retain the full trace.')
    sys.exit(1 if fail else 0)
