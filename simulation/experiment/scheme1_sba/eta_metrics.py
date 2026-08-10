# Extract the S4 eta sweep into eta_sweep_s4.csv + three Pareto CSVs.
#
# Usage (python2, stdlib only):
#   cd <repo>/simulation/experiment/scheme1_sba
#   python2 eta_metrics.py
#
# Metric definitions are IMPORTED from metrics.py rather than reimplemented, so
# every sweep number is computed by exactly the same code as the 30-cell main
# matrix.  A second implementation would risk the sweep and the matrix disagreeing
# for reasons that have nothing to do with eta.
#
# eta = CBAP_MIGRATION_RELEASE_RATIO, the fraction of its aggregate rate the old
# (background) side releases to an arriving batch (rdma-hw.cc:1870):
#     oldShare = (1 - eta) * oldAggregate
# Larger eta => background releases more => collective gets capacity sooner.
#
# eta=0.50 is the compiled default (third.cc:159) and s4_config.txt does not
# override it, so the main-matrix cell m_cbapsba_s4_seed2 IS the eta=0.50 point
# and is reused here.  Reuse is verified by config hash in run_eta_sweep.sh.
#
# DCQCN and HPCC S4 rows are copied from the main matrix as fixed reference
# points.  They are NOT re-run: eta does not exist for them.
import csv
import os
import sys

import metrics as M

BASE = os.path.dirname(os.path.abspath(__file__))
LOGS = '/workspaces/yunxiao/matrix_logs'
TAG = 's4'
SEED = 2
RELEASE = 1.9
ETAS = ['0.20', '0.35', '0.50', '0.65', '0.80']

# Metric groups exactly as requested, in reporting order.
INCAST = ['fct_mean_ms', 'fct_p95_ms', 'fct_p99_ms', 'cct_ms',
          'completion_rate_pct', 'incast_agg_gbps', 'incast_fairness_jain']
BG = ['bg_during_gbps', 'bg_min_gbps', 'bg_retention_pct',
      'bg_service_debt_bytes', 'bg_recovery90_ms', 'bg_recovery95_ms',
      'bg_recovery90_ms_never_dipped', 'bg_recovery95_ms_never_dipped',
      'bg_before_gbps', 'bg_fct_ms', 'bg_slowdown']
SYS = ['util_mean', 'queue_mean_bytes', 'queue_p99_bytes', 'queue_peak_bytes',
       'over_qmin_pct', 'over_qmax_pct', 'queue_recovery_ms', 'recovery_rtts',
       'queue_drained', 'ecn_marks', 'pfc_events', 'pfc_pause_total_ns',
       'drops', 'retx_bytes_total', 'retx_events_total',
       'oversub_peak_bytes', 'oversub_peak_ratio', 'oversub_duration_ms',
       'oversub_longest_run_ms', 'qmax_exceed_ratio', 'qmax_bytes']

CTX = ['eta', 'cell', 'kind', 'scenario', 'cc_mode', 'stop_time_s',
       'app_rate_cap_bps', 'sample_us', 'base_rtt_us', 'config_sha256',
       'release_ratio_source']


def eta_tag(eta):
    return eta.replace('.', '')


def cell_name(eta):
    """Directory stem for an eta point.

    eta=0.50 maps to the main-matrix cell, since that run already used the
    default release ratio; the sweep does not duplicate it.
    """
    if eta == '0.50':
        return 'm_cbapsba_%s_seed%d' % (TAG, SEED)
    return 'm_cbapsba_%s_eta%s_seed%d' % (TAG, eta_tag(eta), SEED)


def one_row(eta):
    """Compute every metric for one eta, or return None if the cell is absent."""
    name = cell_name(eta)
    d = os.path.join(BASE, name + '_out')
    cfg_path = os.path.join(BASE, name + '.txt')
    log = os.path.join(LOGS, name + '.log')
    if not os.path.exists(os.path.join(d, 'flow_summary.csv')):
        return None, '%s: no flow_summary.csv' % name
    # Same gate as the matrix: a cell counts only if its own done-flag exists,
    # so a partially written directory is never aggregated.
    flag = os.path.join(LOGS, name + '.done')
    if os.path.isdir(LOGS) and not os.path.exists(flag):
        return None, '%s: no .done flag (incomplete run)' % name

    cfg = M.read_cfg(cfg_path)
    M.SAMPLE_US = M.cfg_float(cfg, 'CRFM_TRACE_SAMPLE_US', 10.0)
    M.BASE_RTT_US = M.base_rtt_us_from_log(log)
    sim_end = M.cfg_float(cfg, 'SIMULATOR_STOP_TIME')
    bg_cap = M.cfg_float(cfg, 'APP_RATE_CAP_BPS', 0.0)
    bg_ids = M.cfg_id_list(cfg, 'APP_RATE_CAP_FLOW')
    qmax = M.link_qmax(BASE, cfg)
    bg_srcs = M.bg_srcs_for(d, bg_ids)

    # The debt window is the scenario stop time, identical for every eta because
    # run_eta_sweep.sh forces STOP=5.5 and asserts the config differs in exactly
    # one line.  Using each cell's own stop time would be wrong only if they
    # diverged; they cannot here, and the check below proves it per row.
    debt_window = sim_end

    row = {'eta': eta, 'cell': name, 'kind': 'cbapsba_eta',
           'scenario': cfg.get('SCENARIO', TAG),
           'cc_mode': cfg.get('CC_MODE', ''),
           'stop_time_s': sim_end,
           'app_rate_cap_bps': bg_cap,
           'sample_us': M.SAMPLE_US,
           'base_rtt_us': M.BASE_RTT_US,
           'config_sha256': M.sha_head(cfg_path),
           'release_ratio_source': cfg.get('CBAP_MIGRATION_RELEASE_RATIO',
                                           'default(0.5)')}
    inc = M.incast_metrics(d, bg_srcs, RELEASE)
    row.update(inc)
    cct = inc.get('cct_ms', M.NAN)
    row.update(M.background_metrics(d, bg_srcs, RELEASE, sim_end, bg_cap,
                                    bg_ids, debt_window, cct))
    wend = RELEASE + (cct / 1000.0) if not M.isnan(cct) else None
    row.update(M.system_metrics(d, RELEASE, qmax, log, wend))
    return row, None


def reference_rows():
    """DCQCN and HPCC S4 rows lifted verbatim from the main matrix report.

    Reference points only -- eta is undefined for them, so 'eta' is blank and
    'kind' marks them as fixed baselines that were not re-run.
    """
    p = os.path.join(BASE, 'final_report', 'final_results.csv')
    if not os.path.exists(p):
        return [], ['final_results.csv absent; no reference points added']
    out, warn = [], []
    f = open(p)
    try:
        for r in csv.DictReader(f):
            if r.get('scenario_tag') != TAG:
                continue
            if r.get('algorithm') not in ('dcqcn', 'hpcc'):
                continue
            r = dict(r)
            r['eta'] = ''
            r['kind'] = 'reference_%s' % r['algorithm']
            r['cell'] = 'm_%s_%s_seed%d' % (r['algorithm'], TAG, SEED)
            r['release_ratio_source'] = 'n/a'
            out.append(r)
    finally:
        f.close()
    if not out:
        warn.append('no dcqcn/hpcc %s rows found in final_results.csv' % TAG)
    return out, warn


def fnum(row, key):
    v = row.get(key, '')
    if v in (None, ''):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:
        return None
    return f


def write_main(rows, path):
    fields = CTX + INCAST + BG + SYS
    extra = []
    for r in rows:
        for k in r:
            if k not in fields and k not in extra and k.startswith('link_'):
                extra.append(k)
    fields = fields + sorted(extra)
    f = open(path, 'w')
    try:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow(r)
    finally:
        f.close()
    return fields


PARETOS = [
    ('paretoA_retention_vs_p99fct.csv',
     'bg_retention_pct', 'background throughput retention (%)',
     'fct_p99_ms', 'incast p99 FCT (ms)'),
    ('paretoB_debt_vs_cct.csv',
     'bg_service_debt_bytes', 'background service debt (bytes)',
     'cct_ms', 'collective completion time (ms)'),
    ('paretoC_queue_vs_p99fct.csv',
     'queue_p99_bytes', 'bottleneck queue p99 (bytes)',
     'fct_p99_ms', 'incast p99 FCT (ms)'),
    # Pareto B is degenerate in S4: the 4 GB background flow finishes inside the
    # 5.5 s stop time at every eta, so service debt is exactly 0 for all five
    # points and for both reference algorithms -- the x-axis collapses to a
    # line.  Debt is still emitted above (it is the requested pairing, and its
    # being zero is itself a finding), but B2 substitutes the background
    # minimum, which is defined and discriminating here, so the debt-side
    # trade-off is still plottable.
    ('paretoB2_bgmin_vs_cct.csv',
     'bg_min_gbps', 'background minimum throughput (Gbps)',
     'cct_ms', 'collective completion time (ms)'),
]


def write_pareto(rows, outdir):
    made = []
    for fn, xk, xl, yk, yl in PARETOS:
        f = open(os.path.join(outdir, fn), 'w')
        try:
            w = csv.writer(f)
            w.writerow(['label', 'kind', 'eta', 'x_metric', 'x_value',
                        'x_label', 'y_metric', 'y_value', 'y_label'])
            for r in rows:
                x, y = fnum(r, xk), fnum(r, yk)
                if x is None or y is None:
                    continue
                if r['kind'] == 'cbapsba_eta':
                    label = 'eta=%s' % r['eta']
                else:
                    label = r['kind'].replace('reference_', '').upper()
                w.writerow([label, r['kind'], r.get('eta', ''),
                            xk, '%.6f' % x, xl, yk, '%.6f' % y, yl])
        finally:
            f.close()
        made.append(fn)
    return made


def trend_report(rows):
    """Check the measured trends against the mechanism's predicted direction.

    Predicted, from oldShare = (1-eta)*oldAggregate:
      eta up -> incast FCT/CCT down, background retention down,
                service debt up, queue pressure up (or flat).
    Non-monotonicity is REPORTED, never tuned away.
    """
    ok = [r for r in rows if r['kind'] == 'cbapsba_eta']
    ok.sort(key=lambda r: float(r['eta']))
    lines = []
    checks = [
        ('fct_p99_ms', 'decrease', 'incast p99 FCT'),
        ('cct_ms', 'decrease', 'CCT'),
        ('bg_retention_pct', 'decrease', 'background retention'),
        ('bg_min_gbps', 'decrease', 'background minimum throughput'),
        ('bg_service_debt_bytes', 'increase', 'background service debt'),
        ('queue_p99_bytes', 'increase', 'queue p99 (clipped: p95==p99==peak)'),
        ('queue_mean_bytes', 'decrease', 'queue mean occupancy'),
        ('over_qmax_pct', 'decrease', 'time above Qmax'),
        ('oversub_duration_ms', 'decrease', 'oversubscription duration'),
    ]
    for key, want, desc in checks:
        vals = [(r['eta'], fnum(r, key)) for r in ok]
        vals = [(e, v) for e, v in vals if v is not None]
        if len(vals) < 2:
            lines.append('  %-26s insufficient data' % desc)
            continue
        seq = [v for _, v in vals]
        span = max(seq) - min(seq)
        scale = max(abs(x) for x in seq) or 1.0
        flat = span <= 1e-12 or (span / scale) < 0.01
        inc = all(seq[i + 1] >= seq[i] for i in range(len(seq) - 1))
        dec = all(seq[i + 1] <= seq[i] for i in range(len(seq) - 1))
        if flat:
            got = 'flat (span %.3g = %.2f%% of scale)' % (
                span, span / scale * 100.0)
            verdict = 'NO TREND -- metric is constant/near-constant here'
        else:
            got = 'increase' if inc else ('decrease' if dec else 'non-monotonic')
            verdict = ('AS PREDICTED' if got == want
                       else 'DEVIATES (expected %s, got %s)' % (want, got))
        lines.append('  %-26s %-14s %s' % (desc, got, verdict))
        lines.append('      ' + '  '.join('%s:%.4g' % (e, v) for e, v in vals))
    return lines


def regime_report(rows):
    """Locate the ECN-activity boundary across eta.

    CBAP-SBA admits explicitly and then hands the flow to a DCQCN steady-state
    backend that only acts on ECN marks.  If a given eta keeps the queue below
    KMIN for the whole run, no packet is ever marked and the backend never
    engages -- the algorithm is running on admission control alone.  That is a
    qualitative change in operating regime, so it is reported separately rather
    than being averaged into a trend line.
    """
    lines = []
    ecn_free, ecn_active = [], []
    for r in sorted([x for x in rows if x['kind'] == 'cbapsba_eta'],
                    key=lambda x: float(x['eta'])):
        marks = fnum(r, 'ecn_marks')
        over = fnum(r, 'over_qmin_pct')
        util = fnum(r, 'util_mean')
        regime = ('admission-only (no ECN)' if (marks is not None and marks == 0)
                  else 'admission + ECN backend')
        (ecn_free if (marks is not None and marks == 0) else ecn_active
         ).append(r['eta'])
        lines.append('  eta=%s  ecn_marks=%-8s over_qmin=%-7s util=%-7s %s' % (
            r['eta'],
            '%d' % marks if marks is not None else 'n/a',
            '%.2f%%' % over if over is not None else 'n/a',
            '%.4f' % util if util is not None else 'n/a',
            regime))
    if ecn_free and ecn_active:
        lines.append('')
        lines.append('  REGIME BOUNDARY between eta=%s (ECN active) and eta=%s '
                     '(ECN silent).' % (max(ecn_active, key=float),
                                        min(ecn_free, key=float)))
        lines.append('  Above the boundary the queue never reaches KMIN, so the '
                     'DCQCN backend')
        lines.append('  receives no marks and CBAP-SBA operates on explicit '
                     'admission alone.')
    return lines


def safety_verdict(rows):
    """Which etas are inside the safe operating region.

    Same rule as the main matrix: no PFC, no drops, no retransmission, and the
    queue drains.  An eta that violates any of these is reported as outside the
    safe band -- it is a boundary result, not a reason to change the algorithm.
    """
    lines = []
    for r in sorted([x for x in rows if x['kind'] == 'cbapsba_eta'],
                    key=lambda x: float(x['eta'])):
        pfc = fnum(r, 'pfc_events') or 0.0
        pause = fnum(r, 'pfc_pause_total_ns') or 0.0
        drop = fnum(r, 'drops') or 0.0
        retx = fnum(r, 'retx_bytes_total') or 0.0
        drained = fnum(r, 'queue_drained')
        comp = fnum(r, 'completion_rate_pct')
        bad = []
        if pfc > 0:
            bad.append('PFC=%g' % pfc)
        if pause > 0:
            bad.append('pause=%gns' % pause)
        if drop > 0:
            bad.append('drops=%g' % drop)
        if retx > 0:
            bad.append('retx=%gB' % retx)
        if drained is not None and drained < 1:
            bad.append('queue not drained')
        if comp is not None and comp < 100.0:
            bad.append('completion=%.1f%%' % comp)
        lines.append('  eta=%s  %s' % (
            r['eta'], 'SAFE' if not bad else 'OUTSIDE SAFE REGION: '
            + ', '.join(bad)))
    return lines


def main():
    outdir = os.path.join(BASE, 'eta_sweep')
    if not os.path.isdir(outdir):
        os.makedirs(outdir)

    rows, problems = [], []
    for eta in ETAS:
        r, err = one_row(eta)
        if r is None:
            problems.append(err)
        else:
            rows.append(r)
    if not rows:
        print('no eta cells found. Run run_eta_sweep.sh first.')
        for p in problems:
            print('  ' + p)
        return 1

    refs, warn = reference_rows()
    problems.extend(warn)
    allrows = rows + refs

    # Every eta must share the scenario constants, or the comparison is not
    # about eta.  Verified from the data, not assumed.
    consts = ['stop_time_s', 'app_rate_cap_bps', 'sample_us']
    for k in consts:
        vals = set('%s' % r.get(k) for r in rows)
        if len(vals) > 1:
            problems.append('%s differs across etas: %s -- NOT comparable'
                            % (k, sorted(vals)))

    main_csv = os.path.join(outdir, 'eta_sweep_s4.csv')
    fields = write_main(allrows, main_csv)
    made = write_pareto(allrows, outdir)

    print('=== eta sweep extraction ===')
    print('  etas found : %s' % ', '.join(r['eta'] for r in rows))
    print('  references : %s' % (', '.join(r['kind'] for r in refs) or 'none'))
    print('  wrote      : %s (%d columns, %d rows)'
          % (os.path.basename(main_csv), len(fields), len(allrows)))
    for m in made:
        print('               %s' % m)
    print('')
    print('=== trend vs mechanism prediction ===')
    for l in trend_report(rows):
        print(l)
    print('')
    print('=== operating regime vs eta ===')
    for l in regime_report(rows):
        print(l)
    print('')
    print('=== safe operating region ===')
    for l in safety_verdict(rows):
        print(l)
    if problems:
        print('')
        print('=== problems ===')
        for p in problems:
            print('  ' + p)
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
