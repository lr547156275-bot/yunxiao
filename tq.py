import csv, os
B='/work/simulation/experiment/scheme1_sba'
print('=== TIMELY on S2: queue depth it experienced, pg0 vs pg3 ===')
for tag,d in (('pg3', B+'/m_timely_s2_seed2_out'),
              ('pg0', B+'/pg0_invalid/analysis_s2')):
    p=os.path.join(d,'selected_link_timeseries.csv')
    if not os.path.exists(p):
        continue
    ts=list(csv.DictReader(open(p)))
    q=[float(r['queue_bytes'] or 0) for r in ts if float(r['time'])>=1.9]
    print('  %s: queue mean=%.0f peak=%.0f' % (tag, sum(q)/len(q), max(q)))
# the pg0 numbers come from the archived report instead
print()
print('=== TIMELY S2 rate outcome, pg0 vs pg3 ===')
print('  pg0: p99 FCT 70.825 ms, incast aggregate 1.895 Gbps')
fs=list(csv.DictReader(open(B+'/m_timely_s2_seed2_out/flow_summary.csv')))
inc=[r for r in fs if r['src']!='65' and r['completed']=='1']
fct=sorted(float(r['fct'])*1000 for r in inc)
print('  pg3: p99 FCT %.3f ms, incast aggregate %.3f Gbps'
      % (fct[int(len(fct)*0.99+0.999)-1], sum(float(r['flow_goodput']) for r in inc)/1e9))
print()
print('=== the queueing-delay term TIMELY sees ===')
print('  a 1.27 MB queue on a 10 Gbps port = %.1f us of queueing delay' % (1276464*8/10e9*1e6))
print('  base RTT (topology) = 15.2 us')
print('  so queueing can inflate RTT by ~%.0fx over base' % (1276464*8/10e9*1e6/15.2))
