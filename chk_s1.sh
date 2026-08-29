set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== S1 DCQCN: is the background flow now ECN-signalled? ==="
python3 - <<'PY'
import csv, os
for a in ('dcqcn','dctcp'):
    d='m_%s_s1_seed2_out' % a
    if not os.path.exists(d+'/flow_summary.csv'): continue
    fs=list(csv.DictReader(open(d+'/flow_summary.csv')))
    inc=[r for r in fs if r['src']!='65' and r['completed']=='1']
    bg=[r for r in fs if r['src']=='65'][0]
    fct=sorted(float(r['fct'])*1000 for r in inc)
    rs=d+'/round_summary.csv'
    cnp=minr='n/a'
    if os.path.exists(rs):
        r={x['flow_id']:x for x in csv.DictReader(open(rs))}
        b=r.get('0',{}); cnp=b.get('cnp_count'); minr=b.get('minimum_rate')
    ts=list(csv.DictReader(open(d+'/selected_link_timeseries.csv')))
    ecn=sum(float(x['ecn_marks_delta']) for x in ts)
    q=[float(x['queue_bytes']) for x in ts if 1.9<=float(x['time'])<=max(float(r['finish_time']) for r in inc)]
    print('  %-7s incast %d/16 mean=%7.3f ms  bg_cnp=%-5s bg_min_rate=%-12s link_ecn=%.0f qpeak=%.0f'
          % (a, len(inc), sum(fct)/len(fct), cnp, minr, ecn, max(q)))
PY
echo "  pg0 reference (invalid): dcqcn mean=17.399 ms, bg_cnp=0, link_ecn=0, qpeak=316496"
