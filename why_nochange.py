import csv, os
os.chdir('/work/simulation/experiment/scheme1_sba')
rows=list(csv.DictReader(open('fx_s3_t025_out/delay_credit.csv')))
print('=== drain IS now computed. Sample of q>q_target rows ===')
bad=[r for r in rows if int(r['queue_bytes'])>int(r['q_target_bytes'])]
for r in bad[:4]:
    print('  q=%-7s q_target=%-6s drain=%-14s total=%-14s total/C=%s'
          % (r['queue_bytes'], r['q_target_bytes'], r['drain_bps'],
             r['total_budget_bps'], r['budget_over_capacity']))
print()
print('=== but does the applied capacity actually follow it? ===')
p='fx_s3_t025_out/applied_rate_audit.csv'
if os.path.exists(p):
    ar=list(csv.DictReader(open(p)))
    print('  applied_rate_audit rows: %d' % len(ar))
    print('  %-10s %-16s %-16s %s' % ('epoch','C_effective_l','target_rate_sum','applied_rate_sum'))
    for r in ar[:5]:
        print('  %-10s %-16s %-16s %s' % (r['epoch'], r['C_effective_l'],
              r['target_rate_sum_bps'], r['applied_rate_sum_bps']))
    ce=set(r['C_effective_l'] for r in ar)
    print('  distinct C_effective_l values: %d  %s' % (len(ce), sorted(ce)[:4]))
print()
print('=== KEY: is the credit-modified capacity reaching the flows? ===')
print('  the credit path sets record.effectiveCapacityBps, but the migration')
print('  replan reads `available` built from plannerCapacityBps -- check which:')
