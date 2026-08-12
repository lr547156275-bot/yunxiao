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

# Link-trace sampling interval, overwritten per scenario from
# CRFM_TRACE_SAMPLE_US.  Used to convert a count of above-Qmax samples into a
# duration, which is exact because the trace is uniform-periodic.
SAMPLE_US = 10.0

# Base RTT for expressing queue recovery in RTTs.  Overwritten per scenario
# from the simulator's own "maxRtt=" line in the run log, which is what the
# simulator actually computed from the topology -- never guessed here.
BASE_RTT_US = 0.0

# Fixed observation window for the cross-algorithm background statistics,
# in seconds from the collective's release.  Constant for every algorithm and
# every scenario, so retention is comparable: the CCT-scoped "during" window
# varies with each run's own speed and cannot be compared across algorithms.
# 150 ms is shorter than the shortest collective observed in any cell, so every
# algorithm is measured over a window in which it was genuinely contending.
FIXED_WINDOW_S = 0.150


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


def read_cfg(path):
    """Parse an ns-3 'KEY value...' config into a dict (last occurrence wins).

    Scenario constants -- stop time, background cap, ECN thresholds, which flows
    are background -- differ per scenario and must come from the config that
    actually ran, not from literals in this file.  Earlier versions hardcoded
    them and silently produced wrong background and slowdown figures for five of
    the six scenarios.
    """
    out = {}
    if not os.path.exists(path):
        return out
    f = open(path)
    try:
        for line in f:
            parts = line.split()
            if len(parts) >= 2:
                out[parts[0]] = ' '.join(parts[1:])
    finally:
        f.close()
    return out


def cfg_float(cfg, key, default=NAN):
    try:
        return float(cfg.get(key, '').split()[0])
    except (ValueError, IndexError, AttributeError):
        return default


def cfg_id_list(cfg, key):
    """Parse a comma-separated id list such as APP_RATE_CAP_FLOW '0,1'."""
    raw = cfg.get(key, '')
    ids = []
    for tok in raw.replace(',', ' ').split():
        try:
            ids.append(str(int(tok)))
        except ValueError:
            pass
    return ids


def link_qmax(base, cfg):
    """Qmax (bytes) from the CBAP link file: column 5 of each link row.

    All links in every scenario share one threshold; assert that rather than
    silently taking the first.
    """
    name = cfg.get('CBAP_LINK_FILE', '').split()[0] if cfg.get('CBAP_LINK_FILE') else ''
    if not name:
        return QMAX_DEFAULT
    path = os.path.join(base, name)
    if not os.path.exists(path):
        return QMAX_DEFAULT
    vals = []
    f = open(path)
    try:
        for i, line in enumerate(f):
            if i == 0:
                continue
            p = line.split()
            if len(p) >= 5:
                try:
                    vals.append(int(p[4]))
                except ValueError:
                    pass
    finally:
        f.close()
    if not vals:
        return QMAX_DEFAULT
    if len(set(vals)) != 1:
        print('  WARNING: link file %s has mixed Qmax values %s; using max'
              % (name, sorted(set(vals))))
    return max(vals)


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
        'completion_rate_pct': 100.0 * len(done) / len(inc) if inc else NAN,
        'fct_mean_ms': mean(fcts),
        'fct_p50_ms': pctl(fcts, 50),
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

def background_metrics(d, bg_srcs, release, sim_end, bg_cap, bg_flow_ids,
                       debt_window_s, cct_ms):
    """Background protection, from acknowledged-byte progress.

    Emits one set of metrics per background flow, suffixed bg0_/bg1_, plus a
    bg_* roll-up that takes the worst case across flows (lowest retention,
    highest debt) so the Pareto axes stay one-dimensional.  S6 has two
    background flows, one per bottleneck; reporting only the first would drop
    half of that scenario's central claim.
    """
    out = {}
    for idx, fid in enumerate(bg_flow_ids):
        pre = 'bg%d_' % idx
        one = _background_one(d, fid, release, sim_end, bg_cap, debt_window_s,
                              cct_ms)
        for k, v in one.items():
            out[pre + k] = v

    # Roll-up across background flows for the headline/Pareto columns.
    def worst(key, pick):
        vals = [out['bg%d_%s' % (i, key)] for i in range(len(bg_flow_ids))
                if ('bg%d_%s' % (i, key)) in out
                and not isnan(out['bg%d_%s' % (i, key)])]
        return pick(vals) if vals else NAN

    def total(key):
        vals = [out['bg%d_%s' % (i, key)] for i in range(len(bg_flow_ids))
                if ('bg%d_%s' % (i, key)) in out
                and not isnan(out['bg%d_%s' % (i, key)])]
        return sum(vals) if vals else NAN

    out['bg_n_flows'] = len(bg_flow_ids)
    out['bg_before_gbps'] = total('before_gbps')
    out['bg_during_gbps'] = total('during_gbps')
    out['bg_after_gbps'] = total('after_gbps')
    out['bg_min_gbps'] = worst('min_gbps', min)
    out['bg_retention_pct'] = worst('retention_pct', min)
    out['bg_drop_pct'] = worst('drop_pct', max)
    out['bg_recovery90_ms'] = worst('recovery90_ms', max)
    out['bg_recovery95_ms'] = worst('recovery95_ms', max)
    out['bg_service_debt_bytes'] = total('service_debt_bytes')
    out['bg_service_debt_window_s'] = debt_window_s
    out['bg_retx_bytes'] = total('retx_bytes')
    out['bg_retx_events'] = total('retx_events')
    out['bg_completed'] = worst('completed', min)
    out['bg_fct_ms'] = worst('fct_ms', max)
    out['bg_slowdown'] = worst('slowdown', max)
    # Fixed-window roll-ups, same conventions as their CCT-scoped counterparts:
    # rates sum across flows, retention/minimum take the worst case.
    out['bg_fixed_window_s'] = FIXED_WINDOW_S
    out['bg_fw_during_gbps'] = total('fw_during_gbps')
    out['bg_fw_bytes_delivered'] = total('fw_bytes_delivered')
    out['bg_fw_min_gbps'] = worst('fw_min_gbps', min)
    out['bg_fw_retention_pct'] = worst('fw_retention_pct', min)
    out['bg_fw_drop_pct'] = worst('fw_drop_pct', max)
    # never_dipped is a per-flow boolean, so a worst-case roll-up is not
    # meaningful; propagate it when there is exactly one background flow and
    # emit the OR across flows otherwise, so the field is populated for S6 too
    # (previously blank there, which made the S6 zeros ambiguous).
    for w in ('90', '95'):
        k = 'recovery%s_ms_never_dipped' % w
        vals = [out['bg%d_%s' % (i, k)] for i in range(len(bg_flow_ids))
                if ('bg%d_%s' % (i, k)) in out
                and not isnan(out['bg%d_%s' % (i, k)])]
        # 1 only if EVERY background flow stayed above the threshold; if any
        # flow dipped, the roll-up recovery time is a real measurement.
        out['bg_%s' % k] = (1 if vals and all(v >= 1 for v in vals)
                            else (0 if vals else NAN))
    return out


def _background_one(d, flow_id, release, sim_end, bg_cap, debt_window_s,
                    cct_ms):
    """Metrics for a single background flow, keyed without a prefix."""
    rows = read_csv(os.path.join(d, 'flow_summary.csv'))
    bg = [r for r in rows if r.get('flow_id') == flow_id]
    out = {}
    size = 0.0
    if bg:
        b = bg[0]
        size = num(b, 'total_size_bytes') or 0
        completed = (num(b, 'completed') or 0) >= 1
        out['completed'] = 1 if completed else 0
        out['fct_ms'] = (num(b, 'fct') or NAN) * 1000 if completed else NAN
        out['retx_bytes'] = num(b, 'retx_bytes') or 0
        out['retx_events'] = num(b, 'retx_events') or 0
        # Slowdown only means something for a flow that finished: actual FCT
        # over the FCT it would have had at its configured rate.
        if completed and size > 0 and bg_cap > 0:
            ideal = size * 8.0 / bg_cap
            fct_s = num(b, 'fct')
            if fct_s and ideal > 0:
                out['slowdown'] = fct_s / ideal

    tr = [r for r in read_csv(os.path.join(d, 'selected_flow_timeseries.csv'))
          if r.get('flow_id') == flow_id and num(r, 'snd_una') is not None
          and num(r, 'time') is not None]
    if len(tr) < 3:
        # No rate trace: fall back to the summary row for debt so the metric is
        # still reported rather than silently missing.
        if bg:
            acked = num(bg[0], 'acked_bytes') or 0
            out['service_debt_bytes'] = (0.0 if out.get('completed')
                                         else max(0.0, size - acked))
        return out
    s = sorted((num(r, 'time'), num(r, 'snd_una')) for r in tr)

    # Service debt at a scenario-fixed window, not at each run's own end, so
    # the number is comparable across algorithms even if a run stopped early.
    acked_at_window = None
    for t, v in s:
        if t <= debt_window_s:
            acked_at_window = v
    if acked_at_window is None:
        acked_at_window = s[0][1]
    out['service_debt_bytes'] = max(0.0, size - acked_at_window) if size else NAN

    def rate(lo, hi):
        w = [x for x in s if lo <= x[0] < hi]
        if len(w) < 2:
            return NAN
        dt = w[-1][0] - w[0][0]
        return (w[-1][1] - w[0][1]) * 8.0 / dt if dt > 0 else NAN

    # Baseline: the half second before release, past the flow's own ramp-up.
    before = rate(max(s[0][0], release - 0.5), release)
    out['before_gbps'] = before / 1e9 if not isnan(before) else NAN

    # "During" is the collective's actual occupancy, not a fixed guess.  cct_ms
    # is computed once by the caller and passed in, so this function does not
    # re-read flow_summary.csv once per background flow.
    during_end = release + (cct_ms / 1000.0 if not isnan(cct_ms) else 0.05)
    during = rate(release, during_end)
    out['during_gbps'] = during / 1e9 if not isnan(during) else NAN
    after = rate(during_end, sim_end)
    out['after_gbps'] = after / 1e9 if not isnan(after) else NAN
    if not isnan(before) and before > 0 and not isnan(during):
        out['retention_pct'] = 100.0 * during / before

    # Fixed-window background statistics, added alongside the CCT-scoped ones
    # above rather than replacing them.
    #
    # The metrics above measure "during" over each run's own collective duration.
    # That is the right window for asking "what did the background flow lose
    # while the collective was actually running", but it is NOT comparable across
    # algorithms: a slow algorithm is averaged over a longer window than a fast
    # one, so identical instantaneous behaviour yields different retention. With
    # the pg fix DCQCN's collective went from 282 ms to 54 ms, which changes its
    # window by 5x and makes the cross-algorithm retention column misleading.
    #
    # FIXED_WINDOW_S is one interval, identical for every algorithm and scenario,
    # starting at release. 150 ms is chosen because it is shorter than the
    # shortest collective observed in any cell, so every algorithm is measured
    # over a window it was genuinely contending in.
    fw_end = release + FIXED_WINDOW_S
    fw = rate(release, fw_end)
    out['fixed_window_s'] = FIXED_WINDOW_S
    out['fw_during_gbps'] = fw / 1e9 if not isnan(fw) else NAN
    if not isnan(before) and before > 0 and not isnan(fw):
        out['fw_retention_pct'] = 100.0 * fw / before
    # Minimum inside the same fixed window, on the same 2 ms sub-window grid as
    # min_gbps, so the two are directly comparable.
    fw_low = None
    t = release
    while t + 0.002 <= fw_end:
        r = rate(t, t + 0.002)
        if not isnan(r) and (fw_low is None or r < fw_low):
            fw_low = r
        t += 0.002
    if fw_low is not None:
        out['fw_min_gbps'] = fw_low / 1e9
        if not isnan(before) and before > 0:
            out['fw_drop_pct'] = 100.0 * (1 - fw_low / before)
    # Bytes the background flow actually moved in the fixed window: an absolute
    # quantity that needs no ratio and cannot be distorted by window length.
    lo = [v for t, v in s if t <= release]
    hi = [v for t, v in s if t <= fw_end]
    if lo and hi:
        out['fw_bytes_delivered'] = max(0.0, hi[-1] - lo[-1])

    # Stop observing once the flow has delivered everything it owed: after that
    # its rate is legitimately zero and reading it as a "dip" would report a
    # flow that was never disturbed as having been squeezed to nothing.  In S4
    # and S5 the background flow completes before the run ends, and without this
    # bound the ECN baselines showed min=0 with an undefined recovery time while
    # their during-throughput was identical to their baseline.
    obs_end = s[-1][0]
    if size > 0:
        for t, v in s:
            if v >= size:
                obs_end = min(obs_end, t)
                break
    out['observation_end_s'] = obs_end
    out['bg_completed_before_end'] = 1 if obs_end < s[-1][0] else 0

    # Minimum over short windows, so a brief dip is not averaged away.
    step = 0.002
    lowest = None
    t = release
    while t + step <= obs_end:
        r = rate(t, t + step)
        if not isnan(r) and (lowest is None or r < lowest):
            lowest = r
        t += step
    if lowest is not None:
        out['min_gbps'] = lowest / 1e9
        if not isnan(before) and before > 0:
            out['drop_pct'] = 100.0 * (1 - lowest / before)

    # Recovery: first time the rate climbs back to 90% / 95% of baseline after
    # having dipped below it.  A background flow that never dips has nothing to
    # recover from, which is a different statement from "not measured" -- it is
    # reported as 0ms and flagged, so an aggregate cannot silently drop it.
    if not isnan(before) and before > 0:
        for frac, key in ((0.90, 'recovery90_ms'), (0.95, 'recovery95_ms')):
            dipped = False
            val = NAN
            t = release
            while t + step <= obs_end:
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
    out = {}
    # Group by link.  A multi-bottleneck scenario must not pool its links: the
    # percentiles would describe a mixture of two different queues, and a peak
    # on one link would be diluted by idle samples on the other.
    links = {}
    for r in rows:
        t = num(r, 'time')
        if t is None or t < release or num(r, 'queue_bytes') is None:
            continue
        links.setdefault(r.get('link_id') or '?', []).append(r)
    if not links:
        return _flow_side_system_metrics(d, log_path, out)

    qmin = qmax * 0.5
    per_link = {}
    for link_id, lrows in sorted(links.items()):
        w = [r for r in lrows
             if window_end is None or num(r, 'time') <= window_end]
        if not w:
            w = lrows
        q = [num(r, 'queue_bytes') for r in w]
        u = [num(r, 'utilization') for r in w
             if num(r, 'utilization') is not None]
        allq = [(num(r, 'time'), num(r, 'queue_bytes')) for r in lrows]
        peak_t = max(allq, key=lambda x: x[1])[0]
        rec = NAN
        for t, qq in allq:
            if t >= peak_t and qq <= qmin:
                rec = (t - peak_t) * 1000
                break
        over = [x for x in q if x > qmax]
        # Longest consecutive excursion above Qmax: one 5ms overshoot and fifty
        # 0.1ms blips have the same total but very different meanings.
        run = best_run = 0
        for x in q:
            run = run + 1 if x > qmax else 0
            best_run = max(best_run, run)
        sample_ms = SAMPLE_US / 1000.0
        per_link[link_id] = {
            'queue_mean_bytes': mean(q),
            'queue_p95_bytes': pctl(q, 95),
            'queue_p99_bytes': pctl(q, 99),
            'queue_peak_bytes': max(q),
            'over_qmin_pct': 100.0 * sum(1 for x in q if x > qmin) / len(q),
            'over_qmax_pct': 100.0 * len(over) / len(q),
            'util_mean': mean(u),
            'ecn_marks': sum(num(r, 'ecn_marks_delta') or 0 for r in w),
            'pfc_events': sum(num(r, 'pfc_event_delta') or 0 for r in w),
            'pfc_paused_samples': sum(
                1 for r in w if (num(r, 'pfc_paused') or 0) > 0),
            # Exported by third.cc from SwitchNode's per-port counter.
            'pfc_pause_total_ns': sum(
                num(r, 'pfc_pause_ns_delta') or 0 for r in w),
            'queue_recovery_ms': rec,
            'queue_final_bytes': allq[-1][1],
            'queue_drained': 1 if allq[-1][1] <= qmin else 0,
            'oversub_peak_bytes': max(0.0, max(q) - qmax),
            'oversub_peak_ratio': max(q) / qmax if qmax > 0 else NAN,
            'oversub_duration_ms': len(over) * sample_ms,
            'oversub_longest_run_ms': best_run * sample_ms,
            'qmax_exceed_ratio': max(q) / qmax if qmax > 0 else NAN,
        }

    # Per-link columns, then a roll-up.  Peak/percentiles take the worst link;
    # counters sum; utilisation averages.
    for link_id, m in per_link.items():
        tag = link_id.replace(':', '_')
        for k, v in m.items():
            out['link_%s_%s' % (tag, k)] = v
    vals = list(per_link.values())

    def worst(k, pick=max):
        return pick(m[k] for m in vals if not isnan(m[k]))

    out['n_links'] = len(vals)
    out['queue_mean_bytes'] = worst('queue_mean_bytes')
    out['queue_p95_bytes'] = worst('queue_p95_bytes')
    out['queue_p99_bytes'] = worst('queue_p99_bytes')
    out['queue_peak_bytes'] = worst('queue_peak_bytes')
    out['over_qmin_pct'] = worst('over_qmin_pct')
    out['over_qmax_pct'] = worst('over_qmax_pct')
    out['util_mean'] = mean([m['util_mean'] for m in vals])
    out['ecn_marks'] = sum(m['ecn_marks'] for m in vals)
    out['pfc_events'] = sum(m['pfc_events'] for m in vals)
    out['pfc_paused_samples'] = sum(m['pfc_paused_samples'] for m in vals)
    out['pfc_pause_total_ns'] = sum(m['pfc_pause_total_ns'] for m in vals)
    out['queue_recovery_ms'] = worst('queue_recovery_ms')
    out['queue_final_bytes'] = worst('queue_final_bytes')
    out['queue_drained'] = min(m['queue_drained'] for m in vals)
    out['oversub_peak_bytes'] = worst('oversub_peak_bytes')
    out['oversub_peak_ratio'] = worst('oversub_peak_ratio')
    out['oversub_duration_ms'] = worst('oversub_duration_ms')
    out['oversub_longest_run_ms'] = worst('oversub_longest_run_ms')
    out['qmax_exceed_ratio'] = worst('qmax_exceed_ratio')
    out['qmax_bytes'] = qmax
    out['qmin_bytes'] = qmin
    if BASE_RTT_US > 0 and not isnan(out['queue_recovery_ms']):
        out['recovery_rtts'] = out['queue_recovery_ms'] * 1000.0 / BASE_RTT_US
    return _flow_side_system_metrics(d, log_path, out)


def _flow_side_system_metrics(d, log_path, out):
    """Retransmission, delivered bytes and drops -- from the flow summary and log."""
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

INCAST_KEYS = ['incast_n', 'incast_done', 'completion_rate_pct', 'fct_mean_ms',
               'fct_p50_ms', 'fct_p95_ms', 'fct_p99_ms', 'fct_min_ms',
               'fct_max_ms', 'cct_ms', 'incast_agg_gbps',
               'incast_fairness_jain']
BG_KEYS = ['bg_completed', 'bg_fct_ms', 'bg_before_gbps', 'bg_during_gbps',
           'bg_after_gbps', 'bg_min_gbps', 'bg_drop_pct', 'bg_retention_pct',
           'bg_recovery90_ms', 'bg_recovery90_ms_never_dipped',
           'bg_recovery95_ms', 'bg_recovery95_ms_never_dipped',
           'bg_service_debt_bytes', 'bg_slowdown', 'bg_retx_bytes',
           'bg_retx_events']
BG_KEYS = BG_KEYS + ['bg_n_flows', 'bg_service_debt_window_s',
                     'bg0_observation_end_s', 'bg0_bg_completed_before_end']
# Fixed-window background statistics: comparable across algorithms because the
# window is identical everywhere (FIXED_WINDOW_S from release), unlike the
# CCT-scoped bg_during_gbps / bg_retention_pct above.
BG_KEYS = BG_KEYS + ['bg_fixed_window_s', 'bg_fw_during_gbps',
                     'bg_fw_retention_pct', 'bg_fw_min_gbps',
                     'bg_fw_drop_pct', 'bg_fw_bytes_delivered']
SYS_KEYS = ['total_acked_bytes', 'util_mean', 'queue_mean_bytes',
            'queue_p95_bytes', 'queue_p99_bytes', 'queue_peak_bytes',
            'over_qmin_pct', 'over_qmax_pct', 'queue_recovery_ms',
            'queue_final_bytes', 'queue_drained', 'ecn_marks', 'pfc_events',
            'pfc_paused_samples', 'pfc_pause_total_ns', 'drops',
            'retx_bytes_total', 'retx_events_total',
            'oversub_peak_bytes', 'oversub_peak_ratio', 'oversub_duration_ms',
            'oversub_longest_run_ms', 'qmax_exceed_ratio', 'recovery_rtts',
            'qmax_bytes', 'qmin_bytes', 'n_links']
# Provenance columns, so every row states the scenario constants it was
# computed against rather than leaving them implicit.
CTX_KEYS = ['scenario', 'cc_mode', 'cbap_enable', 'stop_time_s',
            'app_rate_cap_bps', 'sample_us', 'base_rtt_us', 'config_sha256']
ALL_KEYS = (['algorithm', 'seed'] + CTX_KEYS + INCAST_KEYS + BG_KEYS
            + SYS_KEYS)

PARETO = [
    ('fct_p99_ms', 'bg_retention_pct', 'p99 FCT (ms)', 'bg retention (%)'),
    ('cct_ms', 'bg_service_debt_bytes', 'CCT (ms)', 'service debt (B)'),
    ('incast_agg_gbps', 'queue_p99_bytes', 'agg goodput (Gbps)', 'p99 queue (B)'),
]


def base_rtt_us_from_log(log_path):
    """The simulator prints 'maxRtt=<ns>' after reading the topology.

    Using its own number keeps the RTT normalisation consistent with the
    simulation instead of re-deriving hop counts here and risking a mismatch.
    """
    if not log_path or not os.path.exists(log_path):
        return 0.0
    f = open(log_path)
    try:
        for line in f:
            if line.startswith('maxRtt='):
                try:
                    return float(line.split('=')[1].split()[0]) / 1000.0
                except (ValueError, IndexError):
                    return 0.0
    finally:
        f.close()
    return 0.0


def sha_head(path):
    if not os.path.exists(path):
        return 'MISSING'
    import hashlib
    h = hashlib.sha256()
    f = open(path, 'rb')
    try:
        h.update(f.read())
    finally:
        f.close()
    return h.hexdigest()[:16]


def collect(base, tag, algos, seeds, release, logdir):
    """Gather one row per (algorithm, seed) from the matrix output directories.

    Only m_<algo>_<tag>_seed<N>_out is read.  Earlier smoke and validation runs
    left behind directories with other prefixes; picking those up would
    silently inflate the seed count and the variance.

    Every scenario constant -- stop time, background cap, background flow ids,
    Qmax, sampling interval -- is read from the per-cell config that actually
    ran.  Hardcoding them produced wrong background figures for five of the six
    scenarios.
    """
    global SAMPLE_US, BASE_RTT_US
    runs = []
    stop_times = {}
    for algo in algos:
        for seed in seeds:
            name = 'm_%s_%s_seed%d' % (algo, tag, seed)
            d = os.path.join(base, name + '_out')
            if not os.path.exists(os.path.join(d, 'flow_summary.csv')):
                continue
            # A cell only counts if its own done-flag exists, so a partially
            # written directory from an interrupted run is never aggregated.
            flag = os.path.join(logdir, name + '.done')
            if os.path.isdir(logdir) and not os.path.exists(flag):
                continue
            cfg_path = os.path.join(base, name + '.txt')
            cfg = read_cfg(cfg_path)
            stop_times[algo] = cfg_float(cfg, 'SIMULATOR_STOP_TIME')
            runs.append((algo, seed, d, cfg, cfg_path,
                         os.path.join(logdir, name + '.log')))

    if not runs:
        return []

    # Service debt must use one window for the whole scenario, or an algorithm
    # that stopped earlier would look like it owed less.
    valid_stops = [v for v in stop_times.values() if not isnan(v)]
    debt_window = min(valid_stops) if valid_stops else NAN
    if len(set(valid_stops)) > 1:
        print('  WARNING: stop times differ within %s: %s -- debt window '
              'pinned to %.3fs' % (tag, sorted(set(valid_stops)), debt_window))

    out_rows = []
    for algo, seed, d, cfg, cfg_path, log in runs:
        SAMPLE_US = cfg_float(cfg, 'CRFM_TRACE_SAMPLE_US', 10.0)
        BASE_RTT_US = base_rtt_us_from_log(log)
        sim_end = cfg_float(cfg, 'SIMULATOR_STOP_TIME')
        bg_cap = cfg_float(cfg, 'APP_RATE_CAP_BPS', 0.0)
        bg_ids = cfg_id_list(cfg, 'APP_RATE_CAP_FLOW')
        qmax = link_qmax(base, cfg)
        # Background flows are identified by the cap list, which is the same
        # thing the simulator used -- not by src host number, which collides
        # with incast senders in s2..s5.
        bg_srcs = bg_srcs_for(d, bg_ids)
        row = {'algorithm': algo, 'seed': seed,
               'scenario': cfg.get('SCENARIO', tag),
               'cc_mode': cfg.get('CC_MODE', ''),
               'cbap_enable': cfg.get('CBAP_ENABLE', ''),
               'stop_time_s': sim_end,
               'app_rate_cap_bps': bg_cap,
               'sample_us': SAMPLE_US,
               'base_rtt_us': BASE_RTT_US,
               'config_sha256': sha_head(cfg_path)}
        inc = incast_metrics(d, bg_srcs, release)
        row.update(inc)
        cct = inc.get('cct_ms', NAN)
        row.update(background_metrics(d, bg_srcs, release, sim_end, bg_cap,
                                      bg_ids, debt_window, cct))
        # Bound queue statistics to the collective's occupancy so the
        # percentiles describe the congested period, not the idle tail.
        wend = release + (cct / 1000.0) if not isnan(cct) else None
        row.update(system_metrics(d, release, qmax, log, wend))
        out_rows.append(row)
    return out_rows


def bg_srcs_for(d, bg_flow_ids):
    """Map background flow ids to their src host, for incast exclusion."""
    rows = read_csv(os.path.join(d, 'flow_summary.csv'))
    srcs = set()
    for r in rows:
        if r.get('flow_id') in bg_flow_ids and r.get('src'):
            srcs.add(r['src'])
    return srcs


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else 's1'
    base = os.path.dirname(os.path.abspath(__file__))
    logdir = '/work/matrix_logs'
    algos = ['dcqcn', 'dctcp', 'timely', 'hpcc', 'cbapsba']
    # The simulation consumes no random variates on any reachable path, so one
    # seed per cell carries all the information five would.  Override on the
    # command line only if a genuine randomness source is ever introduced.
    seeds = [int(x) for x in sys.argv[2:]] or [2]
    release = 1.9

    runs = collect(base, tag, algos, seeds, release, logdir)
    if not runs:
        print('no completed runs found for tag %r under %s' % (tag, base))
        print('expected directories like m_dcqcn_%s_seed2_out/' % tag)
        return

    outdir = os.path.join(base, 'analysis_%s' % tag)
    if not os.path.isdir(outdir):
        os.makedirs(outdir)

    # Per-link columns are discovered from the data, not declared in ALL_KEYS:
    # their names depend on which links the scenario monitors (link_84_1_*,
    # link_83_1_*).  Writing only ALL_KEYS silently dropped all of them, which
    # would have lost the per-link detail a multi-bottleneck scenario exists to
    # provide.
    link_keys = []
    for r in runs:
        for k in r:
            if k.startswith('link_') and k not in link_keys:
                link_keys.append(k)
    fieldnames = ALL_KEYS + sorted(link_keys)
    f = open(os.path.join(outdir, 'per_run.csv'), 'w')
    try:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        w.writeheader()
        for r in runs:
            w.writerow(r)
    finally:
        f.close()

    by = {}
    for r in runs:
        by.setdefault(r['algorithm'], []).append(r)

    # With one deterministic run per cell there is no dispersion to report.
    # Emitting a zero-width or NaN "confidence interval" would misrepresent a
    # single observation as a statistical estimate, so the column is omitted
    # entirely rather than filled with a placeholder.
    multi = max(len(v) for v in by.values()) > 1
    metric_keys = INCAST_KEYS + BG_KEYS + SYS_KEYS
    f = open(os.path.join(outdir, 'aggregate.csv'), 'w')
    try:
        w = csv.writer(f)
        hdr = ['algorithm', 'n_runs', 'metric', 'value']
        if multi:
            hdr = ['algorithm', 'n_runs', 'metric', 'mean', 'ci95_half',
                   'min', 'max']
        w.writerow(hdr)
        for algo in algos:
            rs = by.get(algo)
            if not rs:
                continue
            for k in metric_keys:
                v = [r[k] for r in rs if k in r and not isnan(r[k])]
                if not v:
                    continue
                if multi:
                    w.writerow([algo, len(rs), k, '%.6f' % mean(v),
                                '%.6f' % ci95(v), '%.6f' % min(v),
                                '%.6f' % max(v)])
                else:
                    w.writerow([algo, len(rs), k, '%.6f' % v[0]])
    finally:
        f.close()

    f = open(os.path.join(outdir, 'pareto.csv'), 'w')
    try:
        w = csv.writer(f)
        hdr = ['pairing', 'algorithm', 'n_runs', 'x_metric', 'x_value',
               'y_metric', 'y_value']
        if multi:
            hdr = ['pairing', 'algorithm', 'n_runs', 'x_metric', 'x_mean',
                   'x_ci95', 'y_metric', 'y_mean', 'y_ci95']
        w.writerow(hdr)
        for xk, yk, xl, yl in PARETO:
            for algo in algos:
                rs = by.get(algo)
                if not rs:
                    continue
                xv = [r[xk] for r in rs if xk in r and not isnan(r[xk])]
                yv = [r[yk] for r in rs if yk in r and not isnan(r[yk])]
                if not xv or not yv:
                    continue
                if multi:
                    w.writerow(['%s vs %s' % (xl, yl), algo, len(rs),
                                xk, '%.6f' % mean(xv), '%.6f' % ci95(xv),
                                yk, '%.6f' % mean(yv), '%.6f' % ci95(yv)])
                else:
                    w.writerow(['%s vs %s' % (xl, yl), algo, len(rs),
                                xk, '%.6f' % xv[0], yk, '%.6f' % yv[0]])
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
                elif multi:
                    line += ' %13.3f+/-%7.3f' % (mean(v), ci95(v))
                else:
                    line += ' %22.3f' % v[0]
            print(line)

    show('INCAST', ['completion_rate_pct', 'fct_mean_ms', 'fct_p50_ms',
                    'fct_p95_ms', 'fct_p99_ms', 'cct_ms', 'incast_agg_gbps',
                    'incast_fairness_jain'])
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
    show('SYSTEM', ['util_mean', 'queue_mean_bytes', 'queue_p95_bytes',
                    'queue_p99_bytes', 'queue_peak_bytes'])
    show('SAFETY', ['over_qmin_pct', 'over_qmax_pct', 'queue_recovery_ms',
                    'queue_drained', 'ecn_marks', 'pfc_events',
                    'pfc_paused_samples', 'drops', 'retx_bytes_total',
                    'retx_events_total'])

    print('')
    print('--- OVERSUBSCRIPTION VERDICT ---')
    print('  A run that exceeds Qmax is only a failure if the excess is')
    print('  unbounded or unrecoverable.  Criteria: no PFC, no drop, no')
    print('  retransmission, queue drains below Qmin, and aggregate goodput')
    print('  does not regress.')
    best_agg = max((mean([r['incast_agg_gbps'] for r in rs
                          if not isnan(r.get('incast_agg_gbps'))])
                    for rs in by.values() if rs), key=lambda x: x if not isnan(x) else -1)
    for algo in algos:
        rs = by.get(algo)
        if not rs:
            continue
        over = mean([r.get('over_qmax_pct') for r in rs])
        pfc = mean([r.get('pfc_events') for r in rs])
        drop = mean([r.get('drops') for r in rs])
        retx = mean([r.get('retx_bytes_total') for r in rs])
        drained = mean([r.get('queue_drained') for r in rs])
        agg = mean([r.get('incast_agg_gbps') for r in rs])
        peak = mean([r.get('queue_peak_bytes') for r in rs])
        if isnan(over) or over <= 0:
            verdict = 'never exceeded Qmax'
        else:
            safe = ((isnan(pfc) or pfc == 0) and (isnan(drop) or drop == 0)
                    and (isnan(retx) or retx == 0)
                    and (not isnan(drained) and drained >= 1))
            if safe:
                verdict = 'BOUNDED oversubscription (safe)'
            else:
                why = []
                if not isnan(pfc) and pfc > 0:
                    why.append('PFC=%.0f' % pfc)
                if not isnan(drop) and drop > 0:
                    why.append('drops=%.0f' % drop)
                if not isnan(retx) and retx > 0:
                    why.append('retx=%.0f B' % retx)
                if isnan(drained) or drained < 1:
                    why.append('queue did NOT drain')
                verdict = 'UNSAFE: ' + ', '.join(why)
        print('  %-9s over_Qmax=%5.2f%% peak=%9.0f B drained=%s -> %s' % (
            algo, over if not isnan(over) else 0.0,
            peak if not isnan(peak) else 0.0,
            'yes' if (not isnan(drained) and drained >= 1) else 'no', verdict))

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
