set -u
cd /work/simulation/experiment/scheme1_sba/final_report
python3 - <<'PY'
import csv
rows=list(csv.DictReader(open('final_results.csv')))
def g(t,a,k):
    for r in rows:
        if r['scenario_tag']==t and r['algorithm']==a:
            v=r.get(k,'')
            try: return float(v)
            except: return float('nan')
    return float('nan')
T=['s1','s2','s3','s6','s4','s5']
A=['dcqcn','dctcp','timely','hpcc','cbapsba']
for key,lab,fmt in (('fct_p99_ms','incast p99 FCT (ms)','%9.3f'),
                    ('incast_agg_gbps','incast goodput (Gbps)','%9.3f'),
                    ('bg_retention_pct','background retention (%)','%9.2f'),
                    ('bg_min_gbps','background minimum (Gbps)','%9.3f'),
                    ('queue_p99_bytes','queue p99 (bytes)','%9.0f'),
                    ('ecn_marks','ECN marks','%9.0f')):
    print('=== %s ===' % lab)
    print('  %-9s' % 'algo' + ''.join('%11s' % t.upper() for t in T))
    for a in A:
        print('  %-9s' % a + ''.join((fmt % g(t,a,key)).rjust(11) for t in T))
    print()
PY
