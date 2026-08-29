import csv
C=10e9; RTT=15.2e-6
for tag in ('s3','s4'):
    p='/work/simulation/experiment/scheme1_sba/m_cbapsba_%s_seed2_out/selected_link_timeseries.csv'%tag
    ts=list(csv.DictReader(open(p)))
    q=[(float(r['time']), float(r['queue_bytes'] or 0)) for r in ts]
    coll=[v for t,v in q if 1.9<=t<=2.30]
    peak=max(coll); mean=sum(coll)/len(coll)
    hard=C*RTT/8
    over=[v for v in coll if v>hard]
    print('=== %s CBAP-SBA, CURRENT strict-conservation implementation ===' % tag.upper())
    print('  queue mean = %8.0f B (%.2f RTT of delay)' % (mean, mean*8/C/RTT))
    print('  queue peak = %8.0f B (%.2f RTT)' % (peak, peak*8/C/RTT))
    print('  q_hard at 1.00 RTT = %.0f B' % hard)
    print('  samples above q_hard: %d of %d (%.1f%%)  <-- already violating, with NO credit'
          % (len(over), len(coll), len(over)/len(coll)*100))
    # how long above, and how far
    print('  worst excess = %.2f RTT' % (peak*8/C/RTT))
    print()
print('=== why: a 64-way synchronous burst cannot be absorbed in 1 BDP ===')
print('  64 flows x 1 MTU (1048 B) arriving together = %d B = %.2f RTT of queue'
      % (64*1048, 64*1048*8/C/RTT))
print('  i.e. one packet per sender already exceeds 1.00 RTT of queue at this fan-in.')
