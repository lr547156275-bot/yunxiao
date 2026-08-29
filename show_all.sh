set -u
cd /work/simulation/experiment/scheme1_sba/paper_data_pg3
python3 - <<'PY'
import csv
rows=[r for r in csv.DictReader(open('final_results_pg3.csv'))]
T=['s1','s2','s3','s6','s4','s5']; A=['dcqcn','dctcp','timely','hpcc','cbapsba']
def g(t,a,k):
    for r in rows:
        if r['scenario_tag']==t and r['algorithm']==a:
            try: return float(r[k])
            except: return float('nan')
    return float('nan')
def tbl(key,title,fmt='%10.3f'):
    print('=== %s ===' % title)
    print('  %-5s' % 'scen' + ''.join('%11s'%x.upper()[:10] for x in A))
    for t in T:
        print('  %-5s'%t.upper() + ''.join((fmt%g(t,a,key)).rjust(11) for a in A))
    print()
tbl('fct_p99_ms','incast p99 FCT (ms)')
tbl('cct_ms','CCT (ms)')
tbl('incast_agg_gbps','incast aggregate goodput (Gbps)')
tbl('bg_fw_retention_pct','background retention, FIXED 150ms window (%)','%10.2f')
tbl('bg_fw_min_gbps','background minimum, same window (Gbps)')
tbl('queue_p99_bytes','queue p99 (bytes)','%10.0f')
tbl('ecn_marks','ECN marks','%10.0f')
print('=== safety across all 30 cells ===')
for k in ('pfc_events','drops','retx_bytes_total'):
    tot=sum(g(t,a,k) for t in T for a in A if g(t,a,k)==g(t,a,k))
    print('  %-20s total = %.0f' % (k, tot))
PY
