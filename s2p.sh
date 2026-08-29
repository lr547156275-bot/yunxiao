set -u
cd /work/simulation/experiment/scheme1_sba
python3 - <<'PY'
import csv, os
ref={'dcqcn':70.455,'dctcp':70.455,'timely':70.825,'hpcc':15.118,'cbapsba':22.098}
print('=== S2 so far: pg3 vs pg0, plus background CNP (must be >0 now) ===')
print('  %-9s %-11s %-11s %-8s %-10s %-8s %-9s %s' % ('algo','p99 pg3','p99 pg0','ratio','inc_gbps','bg_cnp','ecn','qpeak'))
for a in ('dcqcn','dctcp','timely','hpcc','cbapsba'):
    d='m_%s_s2_seed2_out' % a
    if not os.path.exists(d+'/flow_summary.csv'): continue
    fs=list(csv.DictReader(open(d+'/flow_summary.csv')))
    inc=[r for r in fs if r['src']!='65' and r['completed']=='1']
    if len(inc)<64: continue
    fct=sorted(float(r['fct'])*1000 for r in inc)
    p99=fct[int(len(fct)*0.99+0.999)-1]
    ts=list(csv.DictReader(open(d+'/selected_link_timeseries.csv')))
    ecn=sum(float(x['ecn_marks_delta'] or 0) for x in ts)
    last=max(float(r['finish_time']) for r in inc)
    q=[float(x['queue_bytes'] or 0) for x in ts if 1.9<=float(x['time'])<=last]
    gp=sum(float(r['flow_goodput']) for r in inc)/1e9
    cnp='n/a'
    rs=d+'/round_summary.csv'
    if os.path.exists(rs):
        r={x['flow_id']:x for x in csv.DictReader(open(rs))}
        cnp=r.get('0',{}).get('cnp_count','n/a')
    print('  %-9s %-11.3f %-11.3f %-8.2f %-10.3f %-8s %-9.0f %.0f'
          % (a,p99,ref[a],ref[a]/p99,gp,cnp,ecn,max(q) if q else 0))
PY
