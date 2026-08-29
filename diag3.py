import csv, os
os.chdir('/work/simulation/experiment/scheme1_sba')
rows=list(csv.DictReader(open('fx_s3_t025_out/delay_credit.csv')))
print('=== the latch fired at t=2.000080 s. What was the queue then? ===')
for r in rows[:6]:
    print('  t=%.6f phase=%s q=%-7s q_target=%-6s q_hard=%-7s credit=%-12s drain=%-12s total/C=%s'
          % (int(r['timestamp_ns'])/1e9, r['phase'], r['queue_bytes'],
             r['q_target_bytes'], r['q_hard_bytes'], r['credit_bps'],
             r['drain_bps'], r['budget_over_capacity']))
print()
print('=== ROOT CAUSE: rows where q > q_target -- what does the law output? ===')
bad=[r for r in rows if int(r['queue_bytes'])>int(r['q_target_bytes'])]
print('  such rows: %d' % len(bad))
for r in bad[:5]:
    q=int(r['queue_bytes']); qt=int(r['q_target_bytes']); qh=int(r['q_hard_bytes'])
    print('  q=%-7s q_target=%-6s q_hard=%-7s -> credit=%-12s drain=%-12s total=%s'
          % (q, qt, qh, r['credit_bps'], r['drain_bps'], r['total_budget_bps']))
print()
print('=== is the credit being granted while q is ALREADY above target? ===')
viol=[r for r in bad if int(r['credit_bps'])>0]
print('  rows with q>q_target AND credit>0 : %d  <-- must be 0' % len(viol))
if viol:
    r=viol[0]
    print('  example: q=%s q_target=%s credit=%s' % (r['queue_bytes'], r['q_target_bytes'], r['credit_bps']))
print()
print('=== how many epochs did the credit path see per simulated second? ===')
t0=int(rows[0]['timestamp_ns']); t1=int(rows[-1]['timestamp_ns'])
print('  %d rows over %.6f s -> one row every %.3f us' % (len(rows), (t1-t0)/1e9, (t1-t0)/1e3/len(rows)))
print('  configured H = 15.0 us; epoch = 5 us')
