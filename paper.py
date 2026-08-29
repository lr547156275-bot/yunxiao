# Assemble the paper CSVs from final_results.csv + the eta sweep.
# Pure reorganisation: no new simulation, no recomputation from raw traces.
import csv, os

BASE = '/work/simulation/experiment/scheme1_sba'
SRC  = os.path.join(BASE, 'final_report', 'final_results.csv')
OUT  = os.path.join(BASE, 'paper_data')
if not os.path.isdir(OUT):
    os.makedirs(OUT)

TAGS = ['s1', 's2', 's3', 's6', 's4', 's5']
ALGOS = ['dcqcn', 'dctcp', 'timely', 'hpcc', 'cbapsba']
LABEL = {'dcqcn': 'DCQCN', 'dctcp': 'DCTCP', 'timely': 'TIMELY',
         'hpcc': 'HPCC', 'cbapsba': 'CBAP-SBA'}
SHAPE = {'s1': '16x256KiB bg80%', 's2': '64x256KiB bg80%',
         's3': '64x1MiB bg80%', 's6': 'dual 30+30x256KiB bg80%x2',
         's4': '64x1MiB bg95%', 's5': '64x4MiB bg80%'}

rows = {}
with open(SRC) as f:
    for r in csv.DictReader(f):
        rows[(r['scenario_tag'], r['algorithm'])] = r

def val(t, a, k):
    r = rows.get((t, a))
    if r is None: return ''
    v = r.get(k, '')
    if v in (None, ''): return ''
    try:
        f = float(v)
    except ValueError:
        return v
    if f != f: return ''          # NaN -> blank, never a fake 0
    return '%.6f' % f

def emit(name, cols, note):
    p = os.path.join(OUT, name)
    with open(p, 'w') as f:
        w = csv.writer(f)
        w.writerow(['# ' + note])
        w.writerow(['scenario', 'scenario_shape', 'algorithm'] + [c[0] for c in cols])
        for t in TAGS:
            for a in ALGOS:
                if (t, a) not in rows: continue
                w.writerow([t, SHAPE[t], LABEL[a]] + [val(t, a, c[1]) for c in cols])
    return name

made = []
made.append(emit('t1_fct_cct.csv', [
    ('fct_mean_ms','fct_mean_ms'), ('fct_p50_ms','fct_p50_ms'),
    ('fct_p95_ms','fct_p95_ms'), ('fct_p99_ms','fct_p99_ms'),
    ('fct_min_ms','fct_min_ms'), ('fct_max_ms','fct_max_ms'),
    ('cct_ms','cct_ms'), ('completion_rate_pct','completion_rate_pct'),
    ('incast_n','incast_n')],
    'Incast FCT distribution and collective completion time. Lower is better.'))

made.append(emit('t2_incast_goodput.csv', [
    ('incast_agg_gbps','incast_agg_gbps'),
    ('incast_fairness_jain','incast_fairness_jain'),
    ('total_acked_bytes','total_acked_bytes')],
    'Incast aggregate goodput and intra-collective fairness. Higher is better.'))

made.append(emit('t3_background_protection.csv', [
    ('bg_before_gbps','bg_before_gbps'), ('bg_during_gbps','bg_during_gbps'),
    ('bg_after_gbps','bg_after_gbps'), ('bg_min_gbps','bg_min_gbps'),
    ('bg_retention_pct','bg_retention_pct'),
    ('bg_recovery90_ms','bg_recovery90_ms'),
    ('bg_recovery90_never_dipped','bg_recovery90_ms_never_dipped'),
    ('bg_recovery95_ms','bg_recovery95_ms'),
    ('bg_recovery95_never_dipped','bg_recovery95_ms_never_dipped'),
    ('bg_service_debt_bytes','bg_service_debt_bytes'),
    ('bg_service_debt_window_s','bg_service_debt_window_s'),
    ('bg_fct_ms','bg_fct_ms'), ('bg_slowdown','bg_slowdown'),
    ('bg_completed','bg_completed'), ('bg_n_flows','bg_n_flows')],
    'Background protection. recovery*_never_dipped=1 means the flow never fell '
    'below the threshold, so a 0 recovery time is a measurement, not missing data.'))

made.append(emit('t4_queue.csv', [
    ('queue_mean_bytes','queue_mean_bytes'), ('queue_p95_bytes','queue_p95_bytes'),
    ('queue_p99_bytes','queue_p99_bytes'), ('queue_peak_bytes','queue_peak_bytes'),
    ('over_qmin_pct','over_qmin_pct'), ('over_qmax_pct','over_qmax_pct'),
    ('queue_recovery_ms','queue_recovery_ms'), ('queue_drained','queue_drained'),
    ('oversub_peak_ratio','oversub_peak_ratio'),
    ('oversub_duration_ms','oversub_duration_ms'),
    ('qmax_bytes','qmax_bytes'), ('qmin_bytes','qmin_bytes')],
    'Bottleneck queue occupancy over the collective window. Qmax is the '
    'migration tolerance band (400000 B); KMIN is 400000 B.'))

made.append(emit('t5_system_safety.csv', [
    ('util_mean','util_mean'), ('ecn_marks','ecn_marks'),
    ('pfc_events','pfc_events'), ('pfc_pause_total_ns','pfc_pause_total_ns'),
    ('drops','drops'), ('retx_bytes_total','retx_bytes_total'),
    ('retx_events_total','retx_events_total'),
    ('recovery_rtts','recovery_rtts')],
    'Utilisation and safety. drops counts headroom exhaustion only '
    '(switch-node.cc:193/201 drop silently), so it is a lower bound; '
    'retransmission corroborates it.')

)
# --- Pareto sets -------------------------------------------------------
def pareto(name, xk, xl, yk, yl, note):
    p = os.path.join(OUT, name)
    with open(p, 'w') as f:
        w = csv.writer(f)
        w.writerow(['# ' + note])
        w.writerow(['scenario', 'scenario_shape', 'algorithm',
                    'x_metric', 'x_value', 'x_label',
                    'y_metric', 'y_value', 'y_label'])
        for t in TAGS:
            for a in ALGOS:
                x, y = val(t, a, xk), val(t, a, yk)
                if x == '' or y == '': continue
                w.writerow([t, SHAPE[t], LABEL[a], xk, x, xl, yk, y, yl])
    return name

made.append(pareto('p1_pareto_retention_vs_p99fct.csv',
    'bg_retention_pct', 'background throughput retention (%) - higher better',
    'fct_p99_ms', 'incast p99 FCT (ms) - lower better',
    'Pareto: background protection against incast latency. Note DCQCN/DCTCP/'
    'TIMELY sit at 100% retention only because their collectives cannot '
    'displace the background flow at all.'))

made.append(pareto('p2_pareto_queue_vs_p99fct.csv',
    'queue_p99_bytes', 'bottleneck queue p99 (bytes) - lower better',
    'fct_p99_ms', 'incast p99 FCT (ms) - lower better',
    'Pareto: queue depth against incast latency.'))

print('wrote %d files into paper_data/' % len(made))
for m in made: print('  ' + m)
