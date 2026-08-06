# Phase-1 metrics extractor for the multi-algorithm comparison matrix.
#
# Reads every completed run under experiment/scheme1_sba/m_<algo>_s1_seed<N>_out
# and emits per_run.csv plus an aggregate table with 95% confidence intervals.
#
# S1 flow classification: src 65 is the background flow (4GB, capped 8Gbps,
# starts 0.5s).  All other flows are the incast collective (256KiB, released
# at 1.9s).
#
# Run inside the container:  python2 extract_matrix.py
import csv
import os
import math
import collections

D = '/work/simulation/experiment/scheme1_sba'
LOGS = '/work/matrix_logs'
BG_SRC = '65'
WINDOW_START = 1.9      # collective release time (s)
QMAX_BYTES = 400000     # from s1_cbap_link.txt
BG_TOTAL_BYTES = 4000000000

ALGOS = ['dcqcn', 'hpcc', 'timely', 'dctcp', 'cbapsba']
SEEDS = [2, 3, 4, 5, 6]

NAN = float('nan')


def isnan(x):
    return isinstance(x, float) and math.isnan(x)


def pct(vals, p):
    if not vals:
        return NAN
    s = sorted(vals)
    k = (len(s) - 1) * p / 100.0
    f = int(math.floor(k))
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def mean(v):
    return sum(v) / float(len(v)) if v else NAN


def ci95(v):
    """Half-width of the two-sided 95% CI using the t distribution."""
    n = len(v)
    if n < 2:
        return NAN
    m = mean(v)
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1))
    tcrit = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571}.get(n, 1.96)
    return tcrit * sd / math.sqrt(n)


def read_csv(path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return []
    f = open(path)
    try:
        return list(csv.DictReader(f))
    finally:
        f.close()


def flow_metrics(d):
    rows = read_csv(os.path.join(d, 'flow_summary.csv'))
    inc = [r for r in rows if r['src'] != BG_SRC]
    bg = [r for r in rows if r['src'] == BG_SRC]
    fcts = [float(r['fct']) * 1000 for r in inc]
    gps = [float(r['flow_goodput']) for r in inc]
    out = {
        'incast_n': len(inc),
        'fct_mean_ms': mean(fcts),
        'fct_p95_ms': pct(fcts, 95),
        'fct_p99_ms': pct(fcts, 99),
        'fct_max_ms': max(fcts) if fcts else NAN,
        # The collective completes when its slowest member does.
        'cct_ms': max(fcts) if fcts else NAN,
        'incast_agg_gp_gbps': sum(gps) / 1e9,
        'bg_completed': len(bg),
        'bg_fct_ms': float(bg[0]['fct']) * 1000 if bg else NAN,
        'bg_gp_gbps': float(bg[0]['flow_goodput']) / 1e9 if bg else NAN,
        # A background flow absent from flow_summary.csv never finished, so it
        # still owes its whole transfer.  See the note in the report: this is a
        # lower bound on debt, not the exact residue.
        'bg_service_debt_bytes': 0 if bg else BG_TOTAL_BYTES,
    }
    return out


def link_metrics(d):
    rows = read_csv(os.path.join(d, 'selected_link_timeseries.csv'))
    w = [r for r in rows if float(r['time']) >= WINDOW_START]
    if not w:
        return {}
    q = [int(r['queue_bytes']) for r in w]
    u = [float(r['utilization']) for r in w]
    return {
        'util_mean': mean(u),
        'peak_queue_bytes': max(q),
        'over_qmax_pct': 100.0 * sum(1 for x in q if x > QMAX_BYTES) / len(q),
        'ecn_marks': sum(int(r['ecn_marks_delta']) for r in w),
        'pfc_events': sum(int(r['pfc_event_delta']) for r in w),
    }


def bg_rate_metrics(d):
    """Background protection metrics from the per-flow trace.

    Requires flow 0 (the background flow) to be in ROUND_TRACE_SELECTED_FLOWS.

    Deliberately does NOT use the current_rate column: that writes
    q->m_rate (third.cc FlowTraceTick), which is the CONTROLLER's rate, not
    what reaches the wire.  Under DCQCN with no congestion feedback m_rate
    sits at line rate while UpdateNextAvail paces to the application cap, so
    current_rate overstates delivered throughput by the cap ratio.  Delivered
    rate is differentiated from snd_una, which counts acknowledged bytes.
    """
    rows = read_csv(os.path.join(d, 'selected_flow_timeseries.csv'))
    bg = [r for r in rows if r.get('flow_id') == '0'
          and r.get('snd_una') not in (None, '')]
    if len(bg) < 3:
        return {}
    samples = sorted((float(r['time']), int(r['snd_una'])) for r in bg)

    def delivered(lo, hi):
        """Mean delivered rate (bps) over [lo, hi) from acked-byte progress."""
        win = [s for s in samples if lo <= s[0] < hi]
        if len(win) < 2:
            return NAN
        dt = win[-1][0] - win[0][0]
        db = win[-1][1] - win[0][1]
        return (db * 8.0 / dt) if dt > 0 else NAN

    # Baseline: steady state before the collective, skipping the flow's own
    # ramp-up right after it starts.
    baseline = delivered(WINDOW_START - 0.5, WINDOW_START)
    if isnan(baseline) or baseline <= 0:
        return {}

    # Sliding windows after release, so a dip is visible rather than averaged
    # away over the whole post-release period.
    post = [s for s in samples if s[0] >= WINDOW_START]
    if len(post) < 3:
        return {}
    step = 0.002   # 2ms windows
    lowest = None
    rec = NAN
    t = WINDOW_START
    end = post[-1][0]
    dipped = False
    while t + step <= end:
        r = delivered(t, t + step)
        if not isnan(r):
            if lowest is None or r < lowest:
                lowest = r
            if r < 0.9 * baseline:
                dipped = True
            elif dipped and isnan(rec) and r >= 0.9 * baseline:
                rec = (t - WINDOW_START) * 1000
        t += step
    if lowest is None:
        return {}
    return {
        'bg_baseline_gbps': baseline / 1e9,
        'bg_min_gbps': lowest / 1e9,
        'bg_drop_pct': 100.0 * (1 - lowest / baseline),
        'bg_recovery_ms': rec,
    }


def drop_count(tag, seed):
    """Headroom-exhaustion drops, printed by switch-mmu.cc:38 to stdout."""
    p = os.path.join(LOGS, 'm_%s_s1_seed%d.log' % (tag, seed))
    if not os.path.exists(p):
        return NAN
    n = 0
    f = open(p)
    try:
        for line in f:
            if 'Drop:' in line:
                n += 1
    finally:
        f.close()
    return n


def collect():
    per_run = []
    for tag in ALGOS:
        for seed in SEEDS:
            d = os.path.join(D, 'm_%s_s1_seed%d_out' % (tag, seed))
            if not os.path.exists(os.path.join(d, 'flow_summary.csv')):
                continue
            row = {'algorithm': tag, 'seed': seed}
            row.update(flow_metrics(d))
            row.update(link_metrics(d))
            row.update(bg_rate_metrics(d))
            row['drops'] = drop_count(tag, seed)
            per_run.append(row)
    return per_run


KEYS = ['algorithm', 'seed', 'incast_n', 'fct_mean_ms', 'fct_p95_ms',
        'fct_p99_ms', 'fct_max_ms', 'cct_ms', 'incast_agg_gp_gbps',
        'bg_completed', 'bg_fct_ms', 'bg_gp_gbps', 'bg_baseline_gbps',
        'bg_min_gbps', 'bg_drop_pct', 'bg_recovery_ms',
        'bg_service_debt_bytes', 'util_mean', 'peak_queue_bytes',
        'over_qmax_pct', 'ecn_marks', 'pfc_events', 'drops']


def agg(rows, key):
    v = [r[key] for r in rows if key in r and not isnan(r[key])]
    return (mean(v), ci95(v), len(v)) if v else (NAN, NAN, 0)


def main():
    per_run = collect()
    if not per_run:
        print('no completed runs found under %s' % D)
        return

    if not os.path.isdir(LOGS):
        os.makedirs(LOGS)
    out = open(os.path.join(LOGS, 'per_run.csv'), 'w')
    try:
        w = csv.DictWriter(out, fieldnames=KEYS, extrasaction='ignore')
        w.writeheader()
        for r in per_run:
            w.writerow(r)
    finally:
        out.close()

    by = collections.defaultdict(list)
    for r in per_run:
        by[r['algorithm']].append(r)

    print('per_run.csv written: %d runs' % len(per_run))
    print('')
    print('=== INCAST (collective) ===')
    print('%-9s %2s | %-20s %-20s %-20s %-18s' % (
        'algo', 'n', 'FCT mean (ms)', 'FCT p95 (ms)', 'FCT p99 (ms)',
        'agg goodput (Gbps)'))
    print('-' * 100)
    for tag in ALGOS:
        rs = by.get(tag)
        if not rs:
            continue
        a = agg(rs, 'fct_mean_ms')
        b = agg(rs, 'fct_p95_ms')
        c = agg(rs, 'fct_p99_ms')
        e = agg(rs, 'incast_agg_gp_gbps')
        print('%-9s %2d | %8.3f +/- %-7.3f %8.3f +/- %-7.3f '
              '%8.3f +/- %-7.3f %7.3f +/- %-6.3f' % (
                  tag, len(rs), a[0], a[1], b[0], b[1], c[0], c[1], e[0], e[1]))

    print('')
    print('=== BACKGROUND PROTECTION ===')
    print('%-9s | %-18s %-18s %-16s %-14s %s' % (
        'algo', 'baseline (Gbps)', 'minimum (Gbps)', 'drop %',
        'recovery (ms)', 'debt (MB)'))
    print('-' * 100)
    for tag in ALGOS:
        rs = by.get(tag)
        if not rs:
            continue
        a = agg(rs, 'bg_baseline_gbps')
        b = agg(rs, 'bg_min_gbps')
        c = agg(rs, 'bg_drop_pct')
        e = agg(rs, 'bg_recovery_ms')
        f = agg(rs, 'bg_service_debt_bytes')
        print('%-9s | %6.3f +/- %-7.3f %6.3f +/- %-7.3f %6.2f +/- %-5.2f '
              '%6.1f +/- %-5.1f %8.0f' % (
                  tag, a[0], a[1], b[0], b[1], c[0], c[1], e[0], e[1],
                  f[0] / 1e6 if not isnan(f[0]) else NAN))

    print('')
    print('=== QUEUE / SAFETY ===')
    print('%-9s | %-16s %-14s %-14s %-12s %-10s %s' % (
        'algo', 'util mean', 'peak queue (B)', 'over Qmax %', 'ECN',
        'PFC', 'drops'))
    print('-' * 100)
    for tag in ALGOS:
        rs = by.get(tag)
        if not rs:
            continue
        a = agg(rs, 'util_mean')
        b = agg(rs, 'peak_queue_bytes')
        c = agg(rs, 'over_qmax_pct')
        e = agg(rs, 'ecn_marks')
        f = agg(rs, 'pfc_events')
        g = agg(rs, 'drops')
        print('%-9s | %6.4f +/- %-6.4f %12.0f %8.2f %12.1f %8.1f %8.1f' % (
            tag, a[0], a[1], b[0], c[0], e[0], f[0], g[0]))


if __name__ == '__main__':
    main()
