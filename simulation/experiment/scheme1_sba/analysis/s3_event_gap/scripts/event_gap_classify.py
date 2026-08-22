# -*- coding: utf-8 -*-
# Item 5: EVENT-LEVEL gap reclassification.
#
# This replaces the earlier classification, which read the bottleneck queue from
# selected_link_timeseries.csv (10 us sampling) and judged gaps whose p50 is
# 2,162 ns.  That comparison was invalid: the queue reading could be up to 10 us
# stale relative to the gap it was describing.  Class A there was relabelled
# A_ARTEFACT_STALE_QUEUE_SAMPLE for exactly this reason.
#
# Here the queue depth comes from causal_queue.csv, which records the depth AT
# THE EVENT INSTANT.  Between two consecutive queue events the depth is constant
# by construction (nothing else can change it), so the depth over a gap interval
# is known exactly, not interpolated.
#
# CLASSIFICATION RULE (five mutually exclusive classes, evaluated in order):
#
#   E  SIMULATION_END_CLIPPED   gap touches a window edge -> boundary artefact,
#                               not a physical idle interval
#   A  QUEUE_NONEMPTY_PACER     q_bytes > 0 at EVERY instant in [gap_start,
#                               gap_end].  Only this permits the phrase
#                               "queue non-empty but idle".
#   B  QUEUE_EMPTY_ARRIVAL      q_bytes == 0 at EVERY instant in the gap: the
#                               serializer had nothing to send; the gap is an
#                               arrival gap, not a service defect
#   C  RATE_ACTUATION           mixed occupancy AND a pacer decision (from
#                               causal_pacer.csv) lands inside the gap
#   D  PROPAGATION_OR_UPSTREAM  mixed occupancy, no pacer decision inside, and
#                               the gap is shorter than one packet time
#   U  UNKNOWN                  anything else.  Never folded into another class.
#
# READ-ONLY.  Reads CSVs, writes CSVs.  No simulation, no config, no source.
import csv
import gzip
import hashlib
import os
import statistics as S
import sys

B = '/work/simulation/experiment/scheme1_sba'
OUT = os.path.join(B, 'analysis/s3_event_gap')
CB = os.path.join(B, 'ct_cbap_on_out')
DQ = os.path.join(B, 'ct_dcqcn_on_out')

C = 10e9
ONE_PKT_NS = 1048 * 8 * 1e9 / C          # 838.4 ns for a 1048 B wire packet
T0N, T1N = 2000000000, 2058372997
EDGE_NS = 1000                            # boundary tolerance, both edges


def sha(p):
    if not os.path.exists(p):
        return 'ABSENT'
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 16), b''):
            h.update(c)
    return h.hexdigest()


# ------------------------------------------------------------------ loaders --
def load_queue(d):
    """Event-level queue timeline: [(t_ns, q_bytes_after)] sorted.

    q_bytes_after is the depth that HOLDS from this event until the next one:
      ENQUEUE fires after the counter is incremented -> q_after includes the pkt
      DEQUEUE fires before it is decremented        -> q_after excludes the pkt
    The tracer wrote both columns explicitly so no guessing is needed here.
    """
    p = os.path.join(d, 'causal_queue.csv')
    if not os.path.exists(p):
        return [], {}
    tl, counts = [], {}
    with open(p) as fh:
        for r in csv.DictReader(fh):
            ev = r['event']
            counts[ev] = counts.get(ev, 0) + 1
            if ev in ('ENQUEUE', 'DEQUEUE'):
                tl.append((int(r['time_ns']), int(r['q_bytes_after'])))
    tl.sort()
    return tl, counts


def load_tx(d):
    """Per-packet (begin, end, bytes) on the bottleneck, restricted to W2."""
    p = os.path.join(d, 'tx_serialization.csv')
    if not os.path.exists(p):
        return []
    beg, out = {}, []
    with open(p) as fh:
        for r in csv.DictReader(fh):
            k = (r['link_id'], r['node_id'], r['if_index'], r['packet_uid'])
            t = int(r['time_ns'])
            if r['event'] == 'TX_BEGIN':
                beg[k] = (t, int(r['packet_bytes']))
            elif r['event'] == 'TX_END' and k in beg:
                b, nb = beg.pop(k)
                out.append((b, t, nb))
    out.sort()
    return [x for x in out if x[0] >= T0N and x[1] <= T1N]


def load_pacer(d):
    p = os.path.join(d, 'causal_pacer.csv')
    if not os.path.exists(p):
        return []
    out = []
    with open(p) as fh:
        for r in csv.DictReader(fh):
            out.append((int(r['time_ns']), r.get('event_action', ''),
                        r.get('flow_id', '')))
    out.sort()
    return out


def gaps_of(pr):
    if not pr:
        return []
    g, ce = [], pr[0][1]
    for (s, e, nb) in pr[1:]:
        if s > ce:
            g.append((ce, s, s - ce))
        ce = max(ce, e)
    return g


# --------------------------------------------------------------- occupancy ---
def occupancy(tl, a, b):
    """Exact q_bytes profile over [a, b) from the event timeline.

    Returns (min_q, max_q, n_events_inside, ns_with_q_positive).
    Between events the depth is constant, so the profile is exact.
    """
    if not tl:
        return (None, None, 0, 0)
    # index of the last event at or before a
    lo, hi = 0, len(tl) - 1
    if a < tl[0][0]:
        idx = -1
    else:
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if tl[mid][0] <= a:
                lo = mid
            else:
                hi = mid - 1
        idx = lo
    q = tl[idx][1] if idx >= 0 else 0
    mn = mx = q
    pos_ns = 0
    cur_t, cur_q = a, q
    j = idx + 1
    inside = 0
    while j < len(tl) and tl[j][0] < b:
        seg = tl[j][0] - cur_t
        if cur_q > 0:
            pos_ns += seg
        mn = min(mn, cur_q)
        mx = max(mx, cur_q)
        cur_t, cur_q = tl[j][0], tl[j][1]
        inside += 1
        j += 1
    seg = b - cur_t
    if cur_q > 0:
        pos_ns += seg
    mn = min(mn, cur_q)
    mx = max(mx, cur_q)
    return (mn, mx, inside, pos_ns)


def pacer_inside(pc, a, b):
    return [x for x in pc if a <= x[0] <= b]


def actuation_witness(d):
    """Independent record of when rate commands occurred, from actuation.csv.

    Needed to tell "no pacer row because no rate change happened" apart from
    "no pacer row because the tracer missed it".  Measured for CBAP in W2:
    420 rate_command entries, all at or before 2,000,185,000 ns, and all inside
    the pacer trace's span -- i.e. the pacer trace is COMPLETE, and the absence
    of rows over the remaining 58.19 ms reflects an absence of rate changes,
    not an absence of telemetry.  Class C is therefore decidable everywhere:
    outside the actuation-active prefix there is no actuation to attribute to.
    """
    p = os.path.join(d, 'actuation.csv')
    if not os.path.exists(p):
        return []
    out = []
    with open(p) as fh:
        for r in csv.DictReader(fh):
            if r.get('stage') == 'rate_command':
                try:
                    t = int(r['time_ns'])
                except (KeyError, ValueError):
                    continue
                if T0N <= t <= T1N:
                    out.append(t)
    return sorted(out)


CLASSES = ['E_SIMULATION_END_CLIPPED', 'A_QUEUE_NONEMPTY_PACER',
           'B_QUEUE_EMPTY_ARRIVAL', 'C_RATE_ACTUATION',
           'D_PROPAGATION_OR_UPSTREAM', 'U_UNKNOWN']

ROWS = []
SUMMARY = {}
COUNTS = {}
INTEGRITY = {}

ARMS = [('CBAP', CB), ('DCQCN', DQ)]
SKIPPED = []
for tag, d in list(ARMS):
    # A cell still being written has open CSVs whose final line may be partial.
    # Classifying those would mix a truncated record into the result, so require
    # the completion marker and report the omission explicitly.
    if not os.path.exists(os.path.join(d, 'DONE')):
        SKIPPED.append(tag)
        ARMS = [x for x in ARMS if x[0] != tag]
        print('SKIP %s: cell not complete (no DONE marker) -- not classified'
              % tag)

for tag, d in ARMS:
    tl, evc = load_queue(d)
    pr = load_tx(d)
    pc = load_pacer(d)
    rc = actuation_witness(d)
    COUNTS[tag] = evc
    gp = gaps_of(pr)
    # Coverage check: every in-window rate_command must have pacer telemetry
    # around it, otherwise class C is undecidable and must be reported as such
    # rather than silently resolved to another class.
    p_lo = pc[0][0] if pc else None
    p_hi = pc[-1][0] if pc else None
    rc_uncov = 0 if not rc else len(
        [t for t in rc if p_lo is None or not (p_lo <= t <= p_hi)])

    # --- integrity: event pairing -----------------------------------------
    INTEGRITY[tag] = dict(
        queue_rows=sum(evc.values()),
        enqueue=evc.get('ENQUEUE', 0), dequeue=evc.get('DEQUEUE', 0),
        tx_begin=evc.get('TX_BEGIN', 0), tx_end=evc.get('TX_END', 0),
        # A window boundary legitimately splits at most one packet at each edge
        # (BEGIN before open -> orphan END; BEGIN before close -> orphan END
        # outside).  Verified against the independent tx_serialization recorder,
        # which shows the same asymmetry, and no uid appears twice.
        tx_pairing_ok=(abs(evc.get('TX_BEGIN', 0) - evc.get('TX_END', 0)) <= 2),
        tx_begin_minus_end=evc.get('TX_BEGIN', 0) - evc.get('TX_END', 0),
        enq_deq_delta=evc.get('ENQUEUE', 0) - evc.get('DEQUEUE', 0),
        pacer_rows=len(pc), packets_w2=len(pr), gaps=len(gp),
        queue_timeline_events=len(tl),
        pacer_span_lo=p_lo if p_lo is not None else '',
        pacer_span_hi=p_hi if p_hi is not None else '',
        rate_commands_in_window=len(rc),
        rate_commands_without_pacer_telemetry=rc_uncov,
        pacer_telemetry_complete=(rc_uncov == 0))

    for (gs, ge, dur) in gp:
        mn, mx, ins, pos = occupancy(tl, gs, ge)
        pin = pacer_inside(pc, gs, ge)
        boundary = (gs <= T0N + EDGE_NS) or (ge >= T1N - EDGE_NS)
        if boundary:
            k = 'E_SIMULATION_END_CLIPPED'
        elif mn is not None and mn > 0:
            k = 'A_QUEUE_NONEMPTY_PACER'
        elif mx is not None and mx == 0:
            k = 'B_QUEUE_EMPTY_ARRIVAL'
        elif pin:
            k = 'C_RATE_ACTUATION'
        elif dur < ONE_PKT_NS:
            k = 'D_PROPAGATION_OR_UPSTREAM'
        else:
            k = 'U_UNKNOWN'
        SUMMARY.setdefault(tag, {}).setdefault(k, [])
        SUMMARY[tag][k].append(dur)
        ROWS.append(dict(
            algorithm=tag, gap_start_ns=gs, gap_end_ns=ge, duration_ns=dur,
            q_bytes_min_in_gap='' if mn is None else mn,
            q_bytes_max_in_gap='' if mx is None else mx,
            queue_events_inside_gap=ins,
            ns_with_queue_positive=pos,
            frac_gap_queue_positive='%.6f' % (pos / float(dur)) if dur else '',
            pacer_decisions_inside=len(pin),
            rate_commands_inside=len([t for t in rc if gs <= t <= ge]),
            inside_pacer_coverage=1 if (p_lo is not None and gs >= p_lo
                                        and ge <= p_hi) else 0,
            touches_window_edge=1 if boundary else 0,
            classification=k,
            evidence='event_level_queue_trace'))

# ----------------------------------------------------------------- writers ---
os.makedirs(os.path.join(OUT, 'scripts'), exist_ok=True)


def wcsv(name, rows, gz=False):
    p = os.path.join(OUT, name)
    if not rows:
        open(p, 'w').write('')
        return
    op = gzip.open(p, 'wt', newline='') if gz else open(p, 'w', newline='')
    with op as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)


def pct(v, q):
    if not v:
        return ''
    s = sorted(v)
    return s[min(len(s) - 1, int(q * (len(s) - 1)))]


SROWS = []
for tag, _d in ARMS:
    tot_t = sum(sum(v) for v in SUMMARY.get(tag, {}).values())
    tot_n = sum(len(v) for v in SUMMARY.get(tag, {}).values())
    for k in CLASSES:
        v = SUMMARY.get(tag, {}).get(k, [])
        SROWS.append(dict(
            algorithm=tag, classification=k, n=len(v), total_ns=sum(v),
            share_of_gap_time='%.6f' % (sum(v) / float(tot_t)) if tot_t else '0',
            p50_ns=pct(v, .50), p95_ns=pct(v, .95), p99_ns=pct(v, .99),
            max_ns=max(v) if v else '',
            bytes_equivalent=int(sum(v) * C / 8e9) if v else 0,
            ms_equivalent='%.6f' % (sum(v) / 1e6) if v else '0.000000'))
    SROWS.append(dict(algorithm=tag, classification='TOTAL', n=tot_n,
                      total_ns=tot_t, share_of_gap_time='1.000000',
                      p50_ns='', p95_ns='', p99_ns='', max_ns='',
                      bytes_equivalent=int(tot_t * C / 8e9),
                      ms_equivalent='%.6f' % (tot_t / 1e6)))

wcsv('S3_EVENT_GAP_CLASSIFICATION.csv.gz', ROWS, gz=True)
wcsv('S3_EVENT_GAP_SUMMARY.csv', SROWS)
wcsv('S3_TELEMETRY_INTEGRITY.csv',
     [dict(algorithm=k, **v) for k, v in sorted(INTEGRITY.items())])

# ------------------------------------------------------------------- print ---
print('=== telemetry integrity ===')
for tag, v in sorted(INTEGRITY.items()):
    print('  %-6s queue_rows=%-8d ENQ=%-7d DEQ=%-7d TXB=%-7d TXE=%-7d '
          'pair_ok=%s' % (tag, v['queue_rows'], v['enqueue'], v['dequeue'],
                          v['tx_begin'], v['tx_end'], v['tx_pairing_ok']))
    print('         pacer_rows=%-6d packets_w2=%-7d gaps=%d'
          % (v['pacer_rows'], v['packets_w2'], v['gaps']))

print('=== event-level gap classification (W2) ===')
for tag, _d in ARMS:
    tot_t = sum(sum(v) for v in SUMMARY.get(tag, {}).values())
    print('  %s  total_gap_ns=%d (%.6f ms)' % (tag, tot_t, tot_t / 1e6))
    for k in CLASSES:
        v = SUMMARY.get(tag, {}).get(k, [])
        if not v:
            print('    %-28s n=0' % k)
            continue
        print('    %-28s n=%-5d time=%-9d %6.2f%%  p50=%-6s p99=%-6s max=%s'
              % (k, len(v), sum(v), 100.0 * sum(v) / tot_t if tot_t else 0,
                 pct(v, .50), pct(v, .99), max(v)))

cb = SUMMARY.get('CBAP', {})
dq = SUMMARY.get('DCQCN', {})
if SKIPPED:
    print('=== NOT COMPARABLE: %s skipped, arm-difference table withheld ==='
          % ', '.join(SKIPPED))
print('=== CBAP - DCQCN per class (ns) ===')
for k in CLASSES:
    a = sum(cb.get(k, []))
    b = sum(dq.get(k, []))
    print('    %-28s CBAP=%-9d DCQCN=%-9d diff=%+d' % (k, a, b, a - b))
tc = sum(sum(v) for v in cb.values())
td = sum(sum(v) for v in dq.values())
print('    %-28s CBAP=%-9d DCQCN=%-9d diff=%+d  (%.6f ms)'
      % ('TOTAL', tc, td, tc - td, (tc - td) / 1e6))
u_cb = sum(cb.get('U_UNKNOWN', []))
print('=== unexplained residual ===')
print('    CBAP U_UNKNOWN = %d ns (%.6f ms, %.2f%% of CBAP gap time)'
      % (u_cb, u_cb / 1e6, 100.0 * u_cb / tc if tc else 0))

with open(os.path.join(OUT, 'SHA256SUMS_EVENT_GAP.txt'), 'w') as fh:
    for f in sorted(os.listdir(OUT)):
        p = os.path.join(OUT, f)
        if os.path.isfile(p) and f != 'SHA256SUMS_EVENT_GAP.txt':
            fh.write('%s  %s\n' % (sha(p), f))
print('=== written to %s ===' % OUT)
