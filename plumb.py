import csv, os
os.chdir('/work/simulation/experiment/scheme1_sba')
print('=== did the FLOWS actually get different rates vs legacy? ===')
for n in ('fx_s3_legacy','fx_s3_t025'):
    fs=list(csv.DictReader(open(n+'_out/flow_summary.csv')))
    inc=[r for r in fs if r['src']!='65' and r['completed']=='1']
    gp=[float(r['flow_goodput']) for r in inc]
    print('  %-14s per-flow goodput mean=%.3f Mbps  min=%.3f  max=%.3f'
          % (n, sum(gp)/len(gp)/1e6, min(gp)/1e6, max(gp)/1e6))
print()
print('=== so the credit DID change the outcome (71.0 vs 87.9 ms). ===')
print('=== the constant C_effective_l=9.5G in applied_rate_audit is a DIFFERENT field:')
print('    rdma-hw.cc:889  row.effectiveCapacityBps = link->second.plannerCapacityBps')
print('    i.e. the audit reports plannerCapacityBps, not latest.effectiveCapacityBps.')
print('    plannerCapacityBps is set once (rdma-hw.cc:343) and is an audit contract')
print('    (comment at 3991: "not a controller input"), so it is expected to be flat.')
print()
print('=== the real question: why is q_peak 118424 > q_hard_startup 86072? ===')
rows=list(csv.DictReader(open('fx_s3_t025_out/delay_credit.csv')))
# find the epochs around the peak
mx=max(int(r['queue_bytes']) for r in rows)
peak=[i for i,r in enumerate(rows) if int(r['queue_bytes'])==mx][0]
print('  peak q=%d at row %d, t=%.6f s, phase=%s' % (mx, peak,
      int(rows[peak]['timestamp_ns'])/1e9, rows[peak]['phase']))
print('  the 6 epochs leading up to it:')
for r in rows[max(0,peak-5):peak+2]:
    print('    t=%.6f phase=%s q=%-7s drain=%-12s total/C=%-7s credit=%s'
          % (int(r['timestamp_ns'])/1e9, r['phase'], r['queue_bytes'],
             r['drain_bps'], r['budget_over_capacity'], r['credit_bps']))
