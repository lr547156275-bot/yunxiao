set -u
cd /work/simulation/experiment/scheme1_sba
python3 - <<'PY'
import csv, os
ref={'dcqcn':281.741,'dctcp':281.741,'timely':283.216,'hpcc':60.131,'cbapsba':88.295}
print('=== S3 (64x1MiB, bg80%) pg3 vs pg0 ===')
print('  %-9s %-11s %-11s %-8s %-10s %-9s %s' % ('algo','p99 pg3','p99 pg0','ratio','inc_gbps','ecn','qpeak'))
for a in ('dcqcn','dctcp','timely','hpcc','cbapsba'):
    d='m_%s_s3_seed2_out' % a
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
    print('  %-9s %-11.3f %-11.3f %-8.2f %-10.3f %-9.0f %.0f'
          % (a,p99,ref[a],ref[a]/p99,gp,ecn,max(q) if q else 0))
PY
