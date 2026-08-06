# Unified metrics extraction for the multi-algorithm comparison matrix.
#
# Emits per_run.csv (one row per algorithm x seed), aggregate.csv (mean and
# 95% CI per algorithm) and pareto.csv (the three trade-off pairings), for
# DCQCN, DCTCP, TIMELY, HPCC and CBAP-SBA on the same scenario.
#
# Metric groups:
#   1. Incast   -- mean/p95/p99 FCT, CCT, aggregate goodput, intra-batch fairness
#   2. Background -- throughput before/during/after, minimum, 90%/95% recovery,
#                    completion time, service debt
#   3. System   -- total goodput, utilisation, queue mean/p95/p99/peak, ECN,
#                  PFC, drops, retransmission
#   4. Pareto   -- p99 FCT vs background retention, CCT vs service debt,
#                  aggregate goodput vs p99 queue
#
# Usage:  python2 metrics.py <scenario_tag> [run_dir_glob]
#   e.g.  python2 metrics.py s1
#
# Data-source notes that matter for correctness:
#   * flow_summary.csv records completed flows from qp_finish plus, since the
#     end-of-run sweep was added, unfinished flows with completed=0.  Rows with
#     completed=0 have an empty fct.
#   * Background throughput is differentiated from snd_una (acknowledged
#     bytes).  The current_rate column in selected_flow_timeseries.csv is
#     q->m_rate, the CONTROLLER's rate, which under an application cap or an
#     uncongested run sits above what actually reaches the wire.
#   * Aggregate goodput is total bytes over the completion span, NOT the sum of
#     the per-flow flow_goodput column: 16 flows do not each hold their peak
#     rate simultaneously, so summing that column can exceed line rate.
#   * Drops come from the switch-mmu headroom print in the run log.
import csv
import glob
import math
import os
import sys

QMAX_DEFAULT = 400000
LINE_RATE_BPS = 10000000000.0
NAN = float('nan')


def isnan(x):
    return x is None or (isinstance(x, float) and math.isnan(x))


def num(row, key):
    v = row.get(key)
    if v in (None, ''):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def mean(v):
    v = [x for x in v if not isnan(x)]
    return sum(v) / float(len(v)) if v else NAN


def pctl(vals, p):
    s = sorted(x for x in vals if not isnan(x))
    if not s:
        return NAN
    k = (len(s) - 1) * p / 100.0
    lo = int(math.floor(k))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def ci95(v):
    """Half-width of the two-sided 95% CI (t distribution, small n)."""
    v = [x for x in v if not isnan(x)]
    n = len(v)
    if n < 2:
        return NAN
    m = mean(v)
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1))
    tcrit = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776,
             6: 2.571, 7: 2.447, 8: 2.365}.get(n, 1.96)
    return tcrit * sd / math.sqrt(n)


def read_csv(path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return []
    f = open(path)
    try:
        # A run killed mid-write can leave a truncated final line; DictReader
        # yields None for the missing fields and num() filters those out.
        return list(csv.DictReader(f))
    finally:
        f.close()


def jain(vals):
    """Jain's fairness index: 1.0 = perfectly equal, 1/n = maximally unfair."""
    v = [x for x in vals if not isnan(x) and x > 0]
    if not v:
        return NAN
    s = sum(v)
    sq = sum(x * x for x in v)
    return (s * s) / (len(v) * sq) if sq > 0 else NAN


# ---------------------------------------------------------------- group 1

def incast_metrics(d, bg_srcs, release):
    rows = read_csv(os.path.join(d, 'flow_summary.csv'))
    inc = [r for r in rows if r.get('src') not in bg_srcs]
    done = [r for r in inc if num(r, 'fct') is not None]
    fcts = [num(r, 'fct') * 1000 for r in done]
    if not fcts:
        return {'incast_n': len(inc), 'incast_done': 0}
    finish = [num(r, 'finish_time') for r in done]
    start = [num(r, 'start_time') for r in done]
    span = max(finish) - min(start)
    total_bytes = sum(num(r, 'total_size_bytes') or 0 for r in done)
    # Per-flow delivered rate, used only for the fairness index.
    per_flow = [(num(r, 'total_size_bytes') or 0) * 8.0 / (num(r, 'fct') or 1)
                for r in done]
    return {
        'incast_n': len(inc),
        'incast_done': len(done),
        'fct_mean_ms': mean(fcts),
        'fct_p95_ms': pctl(fcts, 95),
        'fct_p99_ms': pctl(fcts, 99),
        'fct_min_ms': min(fcts),
        'fct_max_ms': max(fcts),
        # The collective finishes when its slowest member does.
        'cct_ms': (max(finish) - release) * 1000,
        'incast_agg_gbps': (total_bytes * 8.0 / span / 1e9) if span > 0 else NAN,
        'incast_fairness_jain': jain(per_flow),
    }


# ---------------------------------------------------------------- group 2

def background_metrics(d, bg_srcs, release, sim_end):
    """Background protection, from acknowledged-byte progress."""
    rows = read_csv(os.path.join(d, 'flow_summary.csv'))
    bg = [r for r in rows if r.get('src') in bg_srcs]
    out = {}
    if bg:
        b = bg[0]
        size = num(b, 'total_size_bytes') or 0
        acked = num(b, 'acked_bytes') or 0
        completed = (num(b, 'completed') or 0) >= 1
        out['bg_completed'] = 1 if completed else 0
        out['bg_fct_ms'] = (num(b, 'fct') or NAN) * 1000 if completed else NAN
        # Service debt: bytes still owed when observation ended.
        out['bg_service_debt_bytes'] = 0 if completed else max(0.0, size - acked)
        out['bg_retx_bytes'] = num(b, 'retx_bytes') or 0
        out['bg_retx_events'] = num(b, 'retx_events') or 0

    tr = [r for r in read_csv(os.path.join(d, 'selected_flow_timeseries.csv'))
          if r.get('flow_id') == '0' and num(r, 'snd_una') is not None
          and num(r, 'time') is not None]
    if len(tr) < 3:
        return out
    s = sorted((num(r, 'time'), num(r, 'snd_una')) for r in tr)

    def rate(lo, hi):
        w = [x for x in s if lo <= x[0] < hi]
        if len(w) < 2:
            return NAN
        dt = w[-1][0] - w[0][0]
        return (w[-1][1] - w[0][1]) * 8.0 / dt if dt > 0 else NAN

    # Baseline: the half second before release, past the flow's own ramp-up.
    before = rate(max(s[0][0], release - 0.5), release)
    out['bg_before_gbps'] = before / 1e9 if not isnan(before) else NAN

    # "During" is the collective's actual occupancy, not a fixed guess.
    inc = incast_metrics(d, bg_srcs, release)
    cct_s = inc.get('cct_ms')
    during_end = release + (cct_s / 1000.0 if not isnan(cct_s) else 0.05)
    during = rate(release, during_end)
    out['bg_during_gbps'] = during / 1e9 if not isnan(during) else NAN
    after = rate(during_end, sim_end)
    out['bg_after_gbps'] = after / 1e9 if not isnan(after) else NAN
    if not isnan(before) and before > 0 and not isnan(during):
        out['bg_retention_pct'] = 100.0 * during / before

    # Minimum over short windows, so a brief dip is not averaged away.
    step = 0.002
    lowest = None
    t = release
    while t + step <= s[-1][0]:
        r = rate(t, t + step)
        if not isnan(r) and (lowest is None or r < lowest):
            lowest = r
        t += step
    if lowest is not None:
        out['bg_min_gbps'] = lowest / 1e9
        if not isnan(before) and before > 0:
            out['bg_drop_pct'] = 100.0 * (1 - lowest / before)

    # Recovery: first time the rate climbs back to 90% / 95% of baseline after
    # having dipped below it.  A background flow that never dips has nothing to
    # recover from, which is a different statement from "not measured" -- it is
    # reported as 0ms and flagged, so an aggregate cannot silently drop it.
    if not isnan(before) and before > 0:
        for frac, key in ((0.90, 'bg_recovery90_ms'), (0.95, 'bg_recovery95_ms')):
            dipped = False
            val = NAN
            t = release
            while t + step <= s[-1][0]:
                r = rate(t, t + step)
                if not isnan(r):
                    if r < frac * before:
                        dipped = True
                    elif dipped:
                        val = (t - release) * 1000
                        break
                t += step
            if not dipped:
                out[key] = 0.0
                out[key + '_never_dipped'] = 1
            else:
                out[key] = val
                out[key + '_never_dipped'] = 0
    return out


# ---------------------------------------------------------------- group 3

def system_metrics(d, release, qmax, log_path, window_end=None):
    """Queue and link statistics.

    window_end bounds the statistics to when the collective was actually on
    the link.  Without it the window runs to SIMULATOR_STOP_TIME and is
    dominated by idle samples -- CBAP-SBA occupies the link for 6ms out of a
    1.1s window, so p95/p99 would both read 0 while the peak sat at 14kB.
    Percentiles have to describe the congested period to mean anything.
    """
    rows = read_csv(os.path.join(d, 'selected_link_timeseries.csv'))
    w = [r for r in rows if num(r, 'time') is not None
         and num(r, 'time') >= release and num(r, 'queue_bytes') is not None
         and (window_end is None or num(r, 'time') <= window_end)]
    out = {}
    if w:
        q = [num(r, 'queue_bytes') for r in w]
        u = [num(r, 'utilization') for r in w if num(r, 'utilization') is not None]
        out.update({
            'queue_mean_bytes': mean(q),
            'queue_p95_bytes': pctl(q, 95),
            'queue_p99_bytes': pctl(q, 99),
            'queue_peak_bytes': max(q),
            'over_qmax_pct': 100.0 * sum(1 for x in q if x > qmax) / len(q),
            'util_mean': mean(u),
            'ecn_marks': sum(num(r, 'ecn_marks_delta') or 0 for r in w),
            'pfc_events': sum(num(r, 'pfc_event_delta') or 0 for r in w),
        })
    fs = read_csv(os.path.join(d, 'flow_summary.csv'))
    out['retx_bytes_total'] = sum(num(r, 'retx_bytes') or 0 for r in fs)
    out['retx_events_total'] = sum(num(r, 'retx_events') or 0 for r in fs)
    # Total delivered bytes across every flow, completed or not.
    out['total_acked_bytes'] = sum(num(r, 'acked_bytes') or 0 for r in fs)

    drops = NAN
    if log_path and os.path.exists(log_path):
        n = 0
        f = open(log_path)
        try:
            for line in f:
                if 'Drop:' in line:
                    n += 1
        finally:
            f.close()
        drops = n
    out['drops'] = drops
    return out


# ---------------------------------------------------------------- driver

INCAST_KEYS = ['incast_n', 'incast_done', 'fct_mean_ms', 'fct_p95_ms',
               'fct_p99_ms', 'fct_min_ms', 'fct_max_ms', 'cct_ms',
               'incast_agg_gbps', 'incast_fairness_jain']
BG_KEYS = ['bg_completed', 'bg_fct_ms', 'bg_before_gbps', 'bg_during_gbps',
           'bg_after_gbps', 'bg_min_gbps', 'bg_drop_pct', 'bg_retention_pct',
           'bg_recovery90_ms', 'bg_recovery90_ms_never_dipped',
           'bg_recovery95_ms', 'bg_recovery95_ms_never_dipped',
           'bg_service_debt_bytes', 'bg_retx_bytes', 'bg_retx_events']
SYS_KEYS = ['total_acked_bytes', 'util_mean', 'queue_mean_bytes',
            'queue_p95_bytes', 'queue_p99_bytes', 'queue_peak_bytes',
            'over_qmax_pct', 'ecn_marks', 'pfc_events', 'drops',
            'retx_bytes_total', 'retx_events_total']
ALL_KEYS = ['algorithm', 'seed'] + INCAST_KEYS + BG_KEYS + SYS_KEYS

PARETO = [
    ('fct_p99_ms', 'bg_retention_pct', 'p99 FCT (ms)', 'bg retention (%)'),
    ('cct_ms', 'bg_service_debt_bytes', 'CCT (ms)', 'service debt (B)'),
    ('incast_agg_gbps', 'queue_p99_bytes', 'agg goodput (Gbps)', 'p99 queue (B)'),
]


def collect(base, tag, algos, seeds, bg_srcs, release, sim_end, qmax, logdir):
    """Gather one row per (algorithm, seed) from the matrix output directories.

    Only m_<algo>_<tag>_seed<N>_out is read.  Earlier smoke and validation
    runs left behind directories with other prefixes; picking those up would
    silently inflate the seed count and the variance.
    """
    runs = []
    for algo in algos:
        for seed in seeds:
            name = 'm_%s_%s_seed%d_out' % (algo, tag, seed)
            d = os.path.join(base, name)
            if not os.path.exists(os.path.join(d, 'flow_summary.csv')):
                continue
            # A cell only counts if its own done-flag exists, so a partially
            # written directory from an interrupted run is never aggregated.
            flag = os.path.join(logdir, 'm_%s_%s_seed%d.done' % (algo, tag, seed))
            if os.path.isdir(logdir) and not os.path.exists(flag):
                continue
            log = os.path.join(logdir, 'm_%s_%s_seed%d.log' % (algo, tag, seed))
            row = {'algorithm': algo, 'seed': seed}
            inc = incast_metrics(d, bg_srcs, release)
            row.update(inc)
            row.update(background_metrics(d, bg_srcs, release, sim_end))
            # Bound queue statistics to the collective's occupancy so the
            # percentiles describe the congested period, not the idle tail.
            cct = inc.get('cct_ms')
            wend = release + (cct / 1000.0) if not isnan(cct) else None
            row.update(system_metrics(d, release, qmax, log, wend))
            runs.append(row)
    return runs


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else 's1'
    base = os.path.dirname(os.path.abspath(__file__))
    logdir = '/work/matrix_logs'
    algos = ['dcqcn', 'dctcp', 'timely', 'hpcc', 'cbapsba']
    seeds = [2, 3, 4, 5, 6]
    # S1/S3 use host 65 as the single background source; S6 adds host 61.
    bg_srcs = set(['65', '61']) if tag == 's6' else set(['65'])
    release = 1.9
    sim_end = 3.0
    qmax = QMAX_DEFAULT

    runs = collect(base, tag, algos, seeds, bg_srcs, release, sim_end,
                   qmax, logdir)
    if not runs:
        print('no completed runs found for tag %r under %s' % (tag, base))
        print('expected directories like m_dcqcn_%s_seed2_out/' % tag)
        return

    outdir = os.path.join(base, 'analysis_%s' % tag)
    if not os.path.isdir(outdir):
        os.makedirs(outdir)

    f = open(os.path.join(outdir, 'per_run.csv'), 'w')
    try:
        w = csv.DictWriter(f, fieldnames=ALL_KEYS, extrasaction='ignore')
        w.writeheader()
        for r in runs:
            w.writerow(r)
    finally:
        f.close()

    by = {}
    for r in runs:
        by.setdefault(r['algorithm'], []).append(r)

    metric_keys = INCAST_KEYS + BG_KEYS + SYS_KEYS
    f = open(os.path.join(outdir, 'aggregate.csv'), 'w')
    try:
        w = csv.writer(f)
        w.writerow(['algorithm', 'n_seeds', 'metric', 'mean', 'ci95_half',
                    'min', 'max'])
        for algo in algos:
            rs = by.get(algo)
            if not rs:
                continue
            for k in metric_keys:
                v = [r[k] for r in rs if k in r and not isnan(r[k])]
                if not v:
                    continue
                w.writerow([algo, len(rs), k, '%.6f' % mean(v),
                            '%.6f' % ci95(v), '%.6f' % min(v),
                            '%.6f' % max(v)])
    finally:
        f.close()

    f = open(os.path.join(outdir, 'pareto.csv'), 'w')
    try:
        w = csv.writer(f)
        w.writerow(['pairing', 'algorithm', 'n_seeds', 'x_metric', 'x_mean',
                    'x_ci95', 'y_metric', 'y_mean', 'y_ci95'])
        for xk, yk, xl, yl in PARETO:
            for algo in algos:
                rs = by.get(algo)
                if not rs:
                    continue
                xv = [r[xk] for r in rs if xk in r and not isnan(r[xk])]
                yv = [r[yk] for r in rs if yk in r and not isnan(r[yk])]
                if not xv or not yv:
                    continue
                w.writerow(['%s vs %s' % (xl, yl), algo, len(rs),
                            xk, '%.6f' % mean(xv), '%.6f' % ci95(xv),
                            yk, '%.6f' % mean(yv), '%.6f' % ci95(yv)])
    finally:
        f.close()

    # ---- console report ----
    print('=' * 108)
    print(' %s  |  %d runs  |  %d algorithms x %d seeds' % (
        tag.upper(), len(runs), len(by), len(seeds)))
    print('=' * 108)

    def show(title, keys, fmt='%10.3f'):
        print('')
        print('--- %s ---' % title)
        hdr = '%-9s %3s' % ('algo', 'n')
        for k in keys:
            hdr += ' %22s' % k[:22]
        print(hdr)
        print('-' * len(hdr))
        for algo in algos:
            rs = by.get(algo)
            if not rs:
                continue
            line = '%-9s %3d' % (algo, len(rs))
            for k in keys:
                v = [r[k] for r in rs if k in r and not isnan(r[k])]
                if not v:
                    line += ' %22s' % '-'
                else:
                    line += ' %13.3f+/-%7.3f' % (mean(v), ci95(v))
            print(line)

    show('INCAST', ['fct_mean_ms', 'fct_p95_ms', 'fct_p99_ms', 'cct_ms',
                    'incast_agg_gbps', 'incast_fairness_jain'])
    show('BACKGROUND', ['bg_before_gbps', 'bg_during_gbps', 'bg_after_gbps',
                        'bg_min_gbps', 'bg_retention_pct', 'bg_recovery90_ms',
                        'bg_recovery95_ms'])
    never = []
    for algo in algos:
        for r in by.get(algo, []):
            if r.get('bg_recovery90_ms_never_dipped') == 1:
                never.append('%s/seed%s' % (algo, r['seed']))
    if never:
        print('  note: background never fell below 90%% of baseline in: %s' %
              ', '.join(never))
        print('        (recovery time reported as 0, not missing)')
    show('SYSTEM', ['util_mean', 'queue_mean_bytes', 'queue_p99_bytes',
                    'queue_peak_bytes', 'ecn_marks', 'pfc_events', 'drops',
                    'retx_bytes_total'])

    print('')
    print('--- PARETO PAIRINGS ---')
    for xk, yk, xl, yl in PARETO:
        print('')
        print('  %s  vs  %s' % (xl, yl))
        for algo in algos:
            rs = by.get(algo)
            if not rs:
                continue
            xv = [r[xk] for r in rs if xk in r and not isnan(r[xk])]
            yv = [r[yk] for r in rs if yk in r and not isnan(r[yk])]
            if not xv or not yv:
                print('    %-9s (missing)' % algo)
                continue
            print('    %-9s x=%12.3f+/-%-9.3f  y=%14.1f+/-%-10.1f' % (
                algo, mean(xv), ci95(xv), mean(yv), ci95(yv)))

    print('')
    print('wrote %s/{per_run,aggregate,pareto}.csv' % outdir)
    incomplete = [r for r in runs
                  if r.get('incast_done', 0) != r.get('incast_n', 0)]
    if incomplete:
        print('')
        print('WARNING: %d run(s) did not complete every incast flow:' %
              len(incomplete))
        for r in incomplete:
            print('  %s seed=%s  %s/%s completed' % (
                r['algorithm'], r['seed'], r.get('incast_done'),
                r.get('incast_n')))


if __name__ == '__main__':
    main()
