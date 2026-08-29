set -u
cd /work/simulation/experiment/scheme1_sba
python3 - <<'PY'
import csv, os
ref={'dcqcn':17.625,'dctcp':17.625,'timely':17.759,'hpcc':4.092,'cbapsba':5.929}
print('=== S1 complete, 5/5: pg3 vs pg0 ===')
print('  %-9s %-11s %-11s %-8s %-10s %-7s %s' % ('algo','p99 pg3','p99 pg0','ratio','inc_gbps','ecn','qpeak'))
res={}
for a in ('dcqcn','dctcp','timely','hpcc','cbapsba'):
    d='m_%s_s1_seed2_out' % a
    fs=list(csv.DictReader(open(d+'/flow_summary.csv')))
    inc=[r for r in fs if r['src']!='65' and r['completed']=='1']
    fct=sorted(float(r['fct'])*1000 for r in inc)
    p99=fct[int(len(fct)*0.99+0.999)-1]
    ts=list(csv.DictReader(open(d+'/selected_link_timeseries.csv')))
    ecn=sum(float(x['ecn_marks_delta'] or 0) for x in ts)
    last=max(float(r['finish_time']) for r in inc)
    q=[float(x['queue_bytes'] or 0) for x in ts if 1.9<=float(x['time'])<=last]
    gp=sum(float(r['flow_goodput']) for r in inc)/1e9
    res[a]=p99
    print('  %-9s %-11.3f %-11.3f %-8.2f %-10.3f %-7.0f %.0f'
          % (a,p99,ref[a],ref[a]/p99,gp,ecn,max(q) if q else 0))
print()
print('=== CBAP-SBA vs baselines on S1, AFTER the fix ===')
c=res['cbapsba']
for a in ('dcqcn','dctcp','timely','hpcc'):
    r=res[a]/c
    print('  vs %-7s %.4f  -> CBAP-SBA is %s' % (a, r, 'FASTER' if r>1 else 'SLOWER by %.2fx'%(1/r)))
PY
