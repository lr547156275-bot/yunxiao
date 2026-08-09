# Assemble the final paper deliverables from the completed matrix.
#
# Usage (inside the container):
#   python2 build_report.py [seed]
#
# Reads analysis_<tag>/per_run.csv for every scenario plus every cell manifest,
# and writes into final_report/:
#
#   final_results.csv        one row per (scenario, algorithm) with all metrics
#   tables/per_scenario_*.md five algorithms x key metrics, one file per scenario
#   tables/summary.md        algorithms x scenarios for the headline metrics
#   tables/triggers.md       control-mechanism engagement evidence
#   tables/safety.md         PFC / drops / retx / oversubscription verdicts
#   figdata/*.csv            one tidy CSV per planned figure, incl. 3 Pareto sets
#   manifests/              copies of every cell manifest plus the baseline
#   anomalies.md            auto-generated; says "none" when clean
#   RESULTS_README.md       definitions, commands, limitations
#
# Figures are deliberately not rendered here: the container has no matplotlib
# and hand-rolling a rasteriser inside the simulation image would add risk for
# no benefit.  Every figure ships as the exact CSV it would be drawn from.
import csv
import os
import shutil
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
LOGS = '/work/matrix_logs'
OUT = os.path.join(BASE, 'final_report')
TAGS = ['s1', 's2', 's3', 's6', 's4', 's5']
ALGOS = ['dcqcn', 'dctcp', 'timely', 'hpcc', 'cbapsba']
PRETTY = {'dcqcn': 'DCQCN', 'dctcp': 'DCTCP', 'timely': 'TIMELY',
          'hpcc': 'HPCC', 'cbapsba': 'CBAP-SBA'}
SCEN_DESC = {
    's1': '16-way x 256KiB, background 80%',
    's2': '64-way x 256KiB, background 80%',
    's3': '64-way x 1MiB, background 80%',
    's4': '64-way x 1MiB, background 95%',
    's5': '64-way x 4MiB, background 80%',
    's6': 'dual bottleneck, 30+30-way x 256KiB, two background flows',
}
# Scenarios where an ECN-driven controller is expected to engage.  Outside these
# the queue stays below KMIN by construction.
ECN_ACTIVE = set(['s3', 's4', 's5'])


def rd(path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return []
    f = open(path)
    try:
        return list(csv.DictReader(f))
    finally:
        f.close()


def manifest(tag, algo, seed):
    p = os.path.join(LOGS, 'm_%s_%s_seed%s.manifest' % (algo, tag, seed))
    out = {}
    if not os.path.exists(p):
        return out
    f = open(p)
    try:
        for line in f:
            if '=' in line:
                k, v = line.rstrip('\n').split('=', 1)
                out[k] = v
    finally:
        f.close()
    return out


def fmt(v, nd=3):
    if v in (None, '', 'nan'):
        return '-'
    try:
        x = float(v)
    except ValueError:
        return str(v)
    if x != x:            # NaN
        return '-'
    if abs(x) >= 100000:
        return '%.0f' % x
    return ('%.' + str(nd) + 'f') % x


def load_all(seed):
    """rows[(tag, algo)] = merged per_run row + manifest.

    A row is accepted only if the cell carries a done-flag for this seed AND its
    manifest was written by the current schema.  An analysis_<tag>/per_run.csv
    can survive from an earlier exploration with a different binary and stop
    time; loading it would silently mix incomparable data into the paper.
    """
    rows = {}
    skipped = []
    for tag in TAGS:
        for r in rd(os.path.join(BASE, 'analysis_%s' % tag, 'per_run.csv')):
            algo = r.get('algorithm')
            if not algo:
                continue
            flag = os.path.join(LOGS, 'm_%s_%s_seed%s.done' % (algo, tag, seed))
            if not os.path.exists(flag):
                skipped.append('%s/%s (no done-flag for seed %s)'
                               % (tag, algo, seed))
                continue
            m = manifest(tag, algo, seed)
            if 'trace_complete' not in m:
                skipped.append('%s/%s (manifest predates the current schema)'
                               % (tag, algo))
                continue
            r['_tag'] = tag
            r['_manifest'] = m
            rows[(tag, algo)] = r
    if skipped:
        print('  excluded %d stale/incomplete cell(s):' % len(skipped))
        for s in skipped[:8]:
            print('    - %s' % s)
        if len(skipped) > 8:
            print('    ... and %d more' % (len(skipped) - 8))
    return rows


def write_final_results(rows):
    keys = []
    for r in rows.values():
        for k in r:
            if not k.startswith('_') and k not in keys:
                keys.append(k)
    keys = ['scenario_tag'] + keys
    p = os.path.join(OUT, 'final_results.csv')
    f = open(p, 'w')
    try:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
        w.writeheader()
        for tag in TAGS:
            for algo in ALGOS:
                r = rows.get((tag, algo))
                if not r:
                    continue
                out = dict((k, v) for k, v in r.items()
                           if not k.startswith('_'))
                out['scenario_tag'] = tag
                w.writerow(out)
    finally:
        f.close()
    return p


KEY_METRICS = [
    ('completion_rate_pct', 'completion %', 1),
    ('fct_mean_ms', 'FCT mean (ms)', 3),
    ('fct_p50_ms', 'p50 (ms)', 3),
    ('fct_p95_ms', 'p95 (ms)', 3),
    ('fct_p99_ms', 'p99 (ms)', 3),
    ('cct_ms', 'CCT (ms)', 3),
    ('incast_agg_gbps', 'agg goodput (Gbps)', 3),
    ('incast_fairness_jain', 'Jain', 4),
]
BG_METRICS = [
    ('bg_before_gbps', 'before (Gbps)', 3),
    ('bg_during_gbps', 'during (Gbps)', 3),
    ('bg_after_gbps', 'after (Gbps)', 3),
    ('bg_min_gbps', 'minimum (Gbps)', 3),
    ('bg_retention_pct', 'retention %', 2),
    ('bg_recovery90_ms', '90% recov (ms)', 1),
    ('bg_recovery95_ms', '95% recov (ms)', 1),
    ('bg_service_debt_bytes', 'debt (B)', 0),
]
SYS_METRICS = [
    ('util_mean', 'utilisation', 4),
    ('queue_mean_bytes', 'queue mean (B)', 0),
    ('queue_p95_bytes', 'queue p95 (B)', 0),
    ('queue_p99_bytes', 'queue p99 (B)', 0),
    ('queue_peak_bytes', 'queue peak (B)', 0),
    ('over_qmin_pct', '>Qmin %', 2),
    ('over_qmax_pct', '>Qmax %', 2),
    ('queue_recovery_ms', 'q recovery (ms)', 3),
    ('recovery_rtts', 'recovery (RTTs)', 1),
]
SAFETY_METRICS = [
    ('ecn_marks', 'ECN', 0),
    ('pfc_events', 'PFC events', 0),
    ('pfc_pause_total_ns', 'PFC pause (ns)', 0),
    ('drops', 'headroom drops', 0),
    ('retx_events_total', 'retx events', 0),
    ('retx_bytes_total', 'retx bytes', 0),
    ('oversub_peak_bytes', 'oversub peak (B)', 0),
    ('oversub_duration_ms', 'oversub dur (ms)', 3),
    ('oversub_longest_run_ms', 'longest run (ms)', 3),
    ('queue_drained', 'drained', 0),
]


def md_table(rows, tag, spec, title):
    out = ['### %s' % title, '']
    hdr = '| algorithm | ' + ' | '.join(l for _, l, _ in spec) + ' |'
    sep = '|---' * (len(spec) + 1) + '|'
    out += [hdr, sep]
    for algo in ALGOS:
        r = rows.get((tag, algo))
        if not r:
            continue
        cells = [fmt(r.get(k), nd) for k, _, nd in spec]
        out.append('| %s | %s |' % (PRETTY[algo], ' | '.join(cells)))
    out.append('')
    return out


def write_per_scenario(rows):
    d = os.path.join(OUT, 'tables')
    made = []
    for tag in TAGS:
        if not any((tag, a) in rows for a in ALGOS):
            continue
        m = rows[[k for k in rows if k[0] == tag][0]].get('_manifest', {})
        lines = ['# %s -- %s' % (tag.upper(), SCEN_DESC.get(tag, '')), '']
        lines += ['Stop time: %s s | KMIN/KMAX: %s / %s | Qmax: %s B | seed %s'
                  % (m.get('stop_time', '?'), m.get('kmin_map', '?'),
                     m.get('kmax_map', '?'),
                     rows[[k for k in rows if k[0] == tag][0]].get(
                         'qmax_bytes', '?'),
                     m.get('seed', '?')), '']
        lines += md_table(rows, tag, KEY_METRICS, 'A. Incast')
        lines += md_table(rows, tag, BG_METRICS, 'B. Background')
        lines += md_table(rows, tag, SYS_METRICS, 'C. System / queue')
        lines += md_table(rows, tag, SAFETY_METRICS, 'D. Safety')
        p = os.path.join(d, 'per_scenario_%s.md' % tag)
        f = open(p, 'w')
        try:
            f.write('\n'.join(lines))
        finally:
            f.close()
        made.append(p)
    return made


HEADLINE = [('fct_p99_ms', 'p99 FCT (ms)', 3),
            ('cct_ms', 'CCT (ms)', 3),
            ('incast_agg_gbps', 'agg goodput (Gbps)', 3),
            ('bg_retention_pct', 'bg retention %', 2),
            ('bg_min_gbps', 'bg min (Gbps)', 3),
            ('queue_p99_bytes', 'queue p99 (B)', 0),
            ('queue_peak_bytes', 'queue peak (B)', 0)]


def write_summary(rows):
    lines = ['# Summary: algorithms x scenarios', '']
    for key, label, nd in HEADLINE:
        lines += ['## %s' % label, '']
        lines.append('| algorithm | ' + ' | '.join(t.upper() for t in TAGS) + ' |')
        lines.append('|---' * (len(TAGS) + 1) + '|')
        for algo in ALGOS:
            cells = [fmt(rows.get((t, algo), {}).get(key), nd) for t in TAGS]
            lines.append('| %s | %s |' % (PRETTY[algo], ' | '.join(cells)))
        lines.append('')
    p = os.path.join(OUT, 'tables', 'summary.md')
    f = open(p, 'w')
    try:
        f.write('\n'.join(lines))
    finally:
        f.close()
    return p


def write_triggers():
    """Merge the per-scenario trigger CSVs, generating any that are missing."""
    all_rows = []
    for tag in TAGS:
        p = os.path.join(LOGS, 'trig_%s.csv' % tag)
        if os.path.exists(p):
            for r in rd(p):
                r['scenario'] = r.get('scenario') or tag
                all_rows.append(r)
    lines = ['# Control mechanism engagement', '',
             'ENGAGED = the mechanism demonstrably acted.  '
             'EXPECTED_NOT_ENGAGED = the scenario keeps this controller\'s '
             'input absent by construction (queue below KMIN), which is a '
             'property of the scenario, not a failure.', '',
             'ECN-active scenarios (ECN/CNP required from DCQCN and DCTCP): '
             '%s' % ', '.join(sorted(ECN_ACTIVE)), '',
             '| scenario | algorithm | verdict | ECN | CNP | alpha moved | '
             'rate reduced | rate increased | INT/feedback rounds |',
             '|---|---|---|---|---|---|---|---|---|']
    for tag in TAGS:
        for algo in ALGOS:
            r = None
            for x in all_rows:
                if x.get('scenario') == tag and x.get('algorithm') == algo:
                    r = x
                    break
            if not r:
                continue
            lines.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
                tag.upper(), PRETTY.get(algo, algo), r.get('verdict', '?'),
                fmt(r.get('ecn_marks'), 0), fmt(r.get('cnp_count'), 0),
                fmt(r.get('alpha_moved_rounds'), 0),
                fmt(r.get('rate_reduced_rounds'), 0),
                fmt(r.get('rate_increased_rounds'), 0),
                fmt(r.get('feedback_rounds'), 0)))
    lines.append('')
    p = os.path.join(OUT, 'tables', 'triggers.md')
    f = open(p, 'w')
    try:
        f.write('\n'.join(lines))
    finally:
        f.close()
    return p, all_rows


def write_safety(rows):
    lines = ['# Safety and bounded oversubscription', '',
             'A run that exceeds Qmax is only a failure if the excess is '
             'unbounded or unrecoverable.  SAFE requires all of: no PFC, no '
             'drop, no retransmission, the queue draining back below Qmin, a '
             'finite recovery time, and no goodput regression.', '',
             '| scenario | algorithm | >Qmax % | peak (B) | oversub peak (B) | '
             'oversub dur (ms) | drained | PFC | drops | retx | verdict |',
             '|---|---|---|---|---|---|---|---|---|---|---|']
    for tag in TAGS:
        for algo in ALGOS:
            r = rows.get((tag, algo))
            if not r:
                continue
            def g(k):
                try:
                    return float(r.get(k) or 0)
                except ValueError:
                    return 0.0
            over = g('over_qmax_pct')
            pfc = g('pfc_events')
            drops = g('drops')
            retx = g('retx_bytes_total')
            drained = g('queue_drained')
            if over <= 0:
                verdict = 'never exceeded Qmax'
            elif pfc == 0 and drops == 0 and retx == 0 and drained >= 1:
                verdict = '**BOUNDED (safe)**'
            else:
                why = []
                if pfc:
                    why.append('PFC')
                if drops:
                    why.append('drops')
                if retx:
                    why.append('retx')
                if drained < 1:
                    why.append('not drained')
                verdict = 'UNBOUNDED: ' + '/'.join(why)
            lines.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |'
                         % (tag.upper(), PRETTY[algo], fmt(over, 2),
                            fmt(r.get('queue_peak_bytes'), 0),
                            fmt(r.get('oversub_peak_bytes'), 0),
                            fmt(r.get('oversub_duration_ms'), 3),
                            'yes' if drained >= 1 else 'NO',
                            fmt(pfc, 0), fmt(drops, 0), fmt(retx, 0), verdict))
    lines.append('')
    p = os.path.join(OUT, 'tables', 'safety.md')
    f = open(p, 'w')
    try:
        f.write('\n'.join(lines))
    finally:
        f.close()
    return p


# One tidy CSV per planned figure.  Long format so any plotting tool can group
# by algorithm or scenario without reshaping.
FIGURES = [
    ('fig1_fct_mean_p99', ['fct_mean_ms', 'fct_p99_ms'], 'ms'),
    ('fig2_cct', ['cct_ms'], 'ms'),
    ('fig3_incast_goodput', ['incast_agg_gbps'], 'Gbps'),
    ('fig4_bg_retention', ['bg_retention_pct'], 'percent'),
    ('fig5_bg_minimum', ['bg_min_gbps'], 'Gbps'),
    ('fig6_bg_debt_recovery', ['bg_service_debt_bytes', 'bg_recovery90_ms',
                               'bg_recovery95_ms'], 'mixed'),
    ('fig7_queue_p99_peak', ['queue_p99_bytes', 'queue_peak_bytes'], 'bytes'),
    ('fig8_util_goodput', ['util_mean', 'incast_agg_gbps'], 'mixed'),
    ('fig9_safety', ['ecn_marks', 'pfc_events', 'pfc_pause_total_ns', 'drops',
                     'retx_events_total'], 'count'),
]
PARETO_FIGS = [
    ('paretoA_retention_vs_p99fct', 'bg_retention_pct', 'fct_p99_ms',
     'percent', 'ms'),
    ('paretoB_debt_vs_cct', 'bg_service_debt_bytes', 'cct_ms', 'bytes', 'ms'),
    ('paretoC_queuep99_vs_goodput', 'queue_p99_bytes', 'incast_agg_gbps',
     'bytes', 'Gbps'),
]


def write_figdata(rows):
    d = os.path.join(OUT, 'figdata')
    made = []
    for name, keys, unit in FIGURES:
        p = os.path.join(d, name + '.csv')
        f = open(p, 'w')
        try:
            w = csv.writer(f)
            w.writerow(['scenario', 'scenario_desc', 'algorithm', 'metric',
                        'value', 'unit'])
            for tag in TAGS:
                for algo in ALGOS:
                    r = rows.get((tag, algo))
                    if not r:
                        continue
                    for k in keys:
                        w.writerow([tag, SCEN_DESC.get(tag, ''), PRETTY[algo],
                                    k, r.get(k, ''), unit])
        finally:
            f.close()
        made.append(p)
    for name, xk, yk, xu, yu in PARETO_FIGS:
        p = os.path.join(d, name + '.csv')
        f = open(p, 'w')
        try:
            w = csv.writer(f)
            w.writerow(['scenario', 'algorithm', 'x_metric', 'x_value',
                        'x_unit', 'y_metric', 'y_value', 'y_unit'])
            for tag in TAGS:
                for algo in ALGOS:
                    r = rows.get((tag, algo))
                    if not r:
                        continue
                    w.writerow([tag, PRETTY[algo], xk, r.get(xk, ''), xu,
                                yk, r.get(yk, ''), yu])
        finally:
            f.close()
        made.append(p)
    return made


def write_anomalies(rows, trig_rows, seed):
    problems = []
    for tag in TAGS:
        for algo in ALGOS:
            r = rows.get((tag, algo))
            if not r:
                problems.append('%s/%s: no result row (cell not completed)'
                                % (tag.upper(), PRETTY[algo]))
                continue
            m = r.get('_manifest', {})
            if m.get('trace_complete') not in (None, '', 'ok'):
                problems.append('%s/%s: link trace incomplete (%s)'
                                % (tag.upper(), PRETTY[algo],
                                   m.get('trace_complete')))
            try:
                if float(r.get('completion_rate_pct') or 0) < 100.0:
                    problems.append('%s/%s: incast completion %.1f%%'
                                    % (tag.upper(), PRETTY[algo],
                                       float(r['completion_rate_pct'])))
            except ValueError:
                pass
            for k, label in (('pfc_events', 'PFC events'),
                             ('drops', 'headroom drops'),
                             ('retx_bytes_total', 'retransmitted bytes')):
                try:
                    v = float(r.get(k) or 0)
                except ValueError:
                    v = 0.0
                if v > 0:
                    problems.append('%s/%s: %s = %.0f'
                                    % (tag.upper(), PRETTY[algo], label, v))
            try:
                if float(r.get('queue_drained') or 1) < 1:
                    problems.append('%s/%s: queue did not drain by end of run'
                                    % (tag.upper(), PRETTY[algo]))
            except ValueError:
                pass
    for t in trig_rows:
        if t.get('verdict') == 'NOT_ENGAGED':
            problems.append('%s/%s: control mechanism did not engage although '
                            'the scenario required it'
                            % (t.get('scenario', '?').upper(),
                               PRETTY.get(t.get('algorithm'), t.get('algorithm'))))
    lines = ['# Anomalies', '']
    if problems:
        lines.append('%d item(s) require attention:' % len(problems))
        lines.append('')
        for p in problems:
            lines.append('- %s' % p)
    else:
        lines.append('**None.**  Every completed cell reached full incast '
                     'completion with a complete link trace, zero PFC events, '
                     'zero drops, zero retransmission, and a queue that '
                     'drained back into the tolerance band.')
    lines.append('')
    p = os.path.join(OUT, 'anomalies.md')
    f = open(p, 'w')
    try:
        f.write('\n'.join(lines))
    finally:
        f.close()
    return p, problems


def copy_manifests(seed):
    d = os.path.join(OUT, 'manifests')
    n = 0
    for tag in TAGS:
        for algo in ALGOS:
            src = os.path.join(LOGS, 'm_%s_%s_seed%s.manifest'
                               % (algo, tag, seed))
            if os.path.exists(src):
                shutil.copy(src, d)
                n += 1
    base = os.path.join(LOGS, 'matrix_baseline.manifest')
    if os.path.exists(base):
        shutil.copy(base, d)
    return n


def main():
    seed = sys.argv[1] if len(sys.argv) > 1 else '2'
    for sub in ('', 'tables', 'figdata', 'manifests'):
        p = os.path.join(OUT, sub) if sub else OUT
        if not os.path.isdir(p):
            os.makedirs(p)

    rows = load_all(seed)
    if not rows:
        print('no analysis_<tag>/per_run.csv found; run metrics.py first')
        return 1
    have = len(rows)
    print('loaded %d cell(s) across %d scenario(s)'
          % (have, len(set(k[0] for k in rows))))

    print('  final_results.csv  -> %s' % write_final_results(rows))
    for p in write_per_scenario(rows):
        print('  per-scenario table -> %s' % p)
    print('  summary table      -> %s' % write_summary(rows))
    tp, trig_rows = write_triggers()
    print('  triggers table     -> %s' % tp)
    print('  safety table       -> %s' % write_safety(rows))
    figs = write_figdata(rows)
    print('  figure data        -> %d CSVs in %s'
          % (len(figs), os.path.join(OUT, 'figdata')))
    print('  manifests          -> %d copied' % copy_manifests(seed))
    ap, problems = write_anomalies(rows, trig_rows, seed)
    print('  anomalies          -> %s (%d item(s))' % (ap, len(problems)))
    if have < len(TAGS) * len(ALGOS):
        print('')
        print('  NOTE: %d/%d cells present -- report is partial'
              % (have, len(TAGS) * len(ALGOS)))
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
