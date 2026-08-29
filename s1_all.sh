set -u
cd /work/simulation/experiment/scheme1_sba
python3 - <<'PY'
import csv, os
print('=== S1 all completed cells: pg3 vs the pg0 reference ===')
ref={'dcqcn':17.625,'dctcp':17.625,'timely':17.759,'hpcc':4.092,'cbapsba':5.929}
print('  %-9s %-12s %-12s %-9s %-10s %-8s %s' % ('algo','p99 pg3','p99 pg0','ratio','inc_gbps','ecn','qpeak'))
for a in ('dcqcn','dctcp','timely','hpcc','cbapsba'):
    d='m_%s_s1_seed2_out' % a
    if not os.path.exists(d+'/flow_summary.csv'): continue
    fs=list(csv.DictReader(open(d+'/flow_summary.csv')))
    inc=[r for r in fs if r['src']!='65' and r['completed']=='1']
    if not inc: continue
    fct=sorted(float(r['fct'])*1000 for r in inc)
    p99=fct[int(len(fct)*0.99+0.999)-1]
    ts=list(csv.DictReader(open(d+'/selected_link_timeseries.csv')))
    ecn=sum(float(x['ecn_marks_delta']) for x in ts)
    last=max(float(r['finish_time']) for r in inc)
    q=[float(x['queue_bytes']) for x in ts if 1.9<=float(x['time'])<=last]
    gp=sum(float(r['flow_goodput']) for r in inc)/1e9
    print('  %-9s %-12.3f %-12.3f %-9.2f %-10.3f %-8.0f %.0f'
          % (a, p99, ref[a], ref[a]/p99, gp, ecn, max(q) if q else 0))
PY
