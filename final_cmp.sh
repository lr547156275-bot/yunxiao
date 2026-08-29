set -u
cd /work/simulation/experiment/scheme1_sba
python3 - <<'PY'
import csv

def flows(p):
    with open(p) as f: return list(csv.DictReader(f))
def series(p):
    with open(p) as f: return list(csv.DictReader(f))

def pctl(v, q):
    v = sorted(v)
    if not v: return float('nan')
    k = int(len(v) * q + 0.999) - 1
    return v[max(0, min(k, len(v) - 1))]

def analyse(stem, release, stop, bgsrc='65'):
    fr = flows('%s_out/flow_summary.csv' % stem)
    inc = [r for r in fr if r['src'] != bgsrc and r['completed'] == '1']
    fct = [float(r['fct']) * 1000 for r in inc]
    gp  = sum(float(r['flow_goodput']) for r in inc)
    fin = max(float(r['finish_time']) for r in inc)
    bg  = [r for r in fr if r['src'] == bgsrc]
    ts = series('%s_out/selected_link_timeseries.csv' % stem)
    win = [r for r in ts if float(r['time']) >= release and float(r['time']) <= fin]
    q  = [float(r['queue_bytes']) for r in win]
    ecn = sum(float(r['ecn_marks_delta']) for r in ts)
    pfc = sum(float(r['pfc_event_delta']) for r in ts)
    pau = sum(float(r['pfc_pause_ns_delta']) for r in ts)
    util = [float(r['utilization']) for r in win]
    kmin = sum(1 for x in q if x > 400000)
    return {
        'n': len(inc),
        'mean': sum(fct)/len(fct), 'p95': pctl(fct,0.95), 'p99': pctl(fct,0.99),
        'cct': (fin - release) * 1000,
        'gp': gp/1e9,
        'q_mean': sum(q)/len(q), 'q_p99': pctl(q,0.99), 'q_peak': max(q),
        'over_kmin': kmin/len(q)*100,
        'ecn': ecn, 'pfc': pfc, 'pause': pau,
        'util': sum(util)/len(util),
        'bg_acked': float(bg[0]['acked_bytes'])/1e9 if bg else float('nan'),
        'retx': sum(float(r['retx_bytes']) for r in fr),
    }

for tag, rel, stop in (('s3', 1.9, 3.0), ('s4', 1.9, 5.5)):
    f = analyse('f_cbapsba_%s_seed2' % tag, rel, stop)
    m = analyse('m_cbapsba_%s_seed2' % tag, rel, stop)
    print('===== %s =====' % tag.upper())
    rows = [
        ('incast completed', '%d' % m['n'], '%d' % f['n'], ''),
        ('mean FCT (ms)', '%.3f' % m['mean'], '%.3f' % f['mean'], '%+.1f%%' % ((f['mean']-m['mean'])/m['mean']*100)),
        ('p95 FCT (ms)', '%.3f' % m['p95'], '%.3f' % f['p95'], '%+.1f%%' % ((f['p95']-m['p95'])/m['p95']*100)),
        ('p99 FCT (ms)', '%.3f' % m['p99'], '%.3f' % f['p99'], '%+.1f%%' % ((f['p99']-m['p99'])/m['p99']*100)),
        ('CCT (ms)', '%.3f' % m['cct'], '%.3f' % f['cct'], '%+.1f%%' % ((f['cct']-m['cct'])/m['cct']*100)),
        ('goodput (Gbps)', '%.3f' % m['gp'], '%.3f' % f['gp'], '%+.1f%%' % ((f['gp']-m['gp'])/m['gp']*100)),
        ('queue mean (B)', '%.0f' % m['q_mean'], '%.0f' % f['q_mean'], '%+.1f%%' % ((f['q_mean']-m['q_mean'])/m['q_mean']*100)),
        ('queue p99 (B)', '%.0f' % m['q_p99'], '%.0f' % f['q_p99'], '%+.1f%%' % ((f['q_p99']-m['q_p99'])/m['q_p99']*100)),
        ('queue peak (B)', '%.0f' % m['q_peak'], '%.0f' % f['q_peak'], '%+.1f%%' % ((f['q_peak']-m['q_peak'])/m['q_peak']*100)),
        ('time > KMIN (%)', '%.2f' % m['over_kmin'], '%.2f' % f['over_kmin'], ''),
        ('ECN marks', '%.0f' % m['ecn'], '%.0f' % f['ecn'], ''),
        ('utilisation', '%.4f' % m['util'], '%.4f' % f['util'], ''),
        ('bg delivered (GB)', '%.3f' % m['bg_acked'], '%.3f' % f['bg_acked'], '%+.2f%%' % ((f['bg_acked']-m['bg_acked'])/m['bg_acked']*100)),
        ('PFC events', '%.0f' % m['pfc'], '%.0f' % f['pfc'], ''),
        ('PFC pause (ns)', '%.0f' % m['pause'], '%.0f' % f['pause'], ''),
        ('retx bytes', '%.0f' % m['retx'], '%.0f' % f['retx'], ''),
    ]
    print('  %-20s %-14s %-14s %s' % ('metric', 'baseline', 'feasible', 'delta'))
    for r in rows:
        print('  %-20s %-14s %-14s %s' % r)
    print()
PY
