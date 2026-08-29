import csv, os
os.chdir('/work/simulation/experiment/scheme1_sba')
print("=== STEP 1a: is the 2.93 s a cross-link / cross-time mixing artifact? ===")
rows=list(csv.DictReader(open('fx_s3_t025_out/delay_credit.csv')))
print('  total credit-trace rows: %d' % len(rows))
links=sorted(set(r['link_id'] for r in rows))
print('  distinct link_id in trace: %s' % links)
t0=int(rows[0]['timestamp_ns'])/1e9; t1=int(rows[-1]['timestamp_ns'])/1e9
print('  trace spans t=%.6f .. %.6f s  (%.3f s)' % (t0,t1,t1-t0))
print()
# the incast lives only in a small window; anything outside is idle-link epochs
fs=list(csv.DictReader(open('fx_s3_t025_out/flow_summary.csv')))
inc=[r for r in fs if r['src']!='65' and r['completed']=='1']
first_start=min(float(r['start_time']) for r in inc)
last_fin=max(float(r['finish_time']) for r in inc)
print('=== the batch actually exists only here ===')
print('  first incast start_time (announcement/admission) = %.6f s' % first_start)
print('  last incast finish                              = %.6f s' % last_fin)
print('  so the batch window is %.3f ms wide' % ((last_fin-first_start)*1000))
print()
inw=[r for r in rows if first_start <= int(r['timestamp_ns'])/1e9 <= last_fin]
out_before=[r for r in rows if int(r['timestamp_ns'])/1e9 < first_start]
out_after=[r for r in rows if int(r['timestamp_ns'])/1e9 > last_fin]
print('=== credit epochs, partitioned by batch lifetime ===')
for lab,g in (('BEFORE admission',out_before),('WITHIN batch',inw),('AFTER last finish',out_after)):
    cred=[r for r in g if int(r['credit_bps'])>0]
    over=[r for r in g if int(r['sum_target_bps'])>10000000000]
    print('  %-18s epochs=%-8d credit>0=%-8d applied>C=%-8d duration=%.1f us'
          % (lab, len(g), len(cred), len(over), len(g)*5.0))
print()
print('=== VERDICT ===')
if len(out_before)+len(out_after) > len(inw):
    print('  The 2.93 s is DOMINATED by epochs outside the batch lifetime.')
    print('  The credit path runs every epoch for the whole 3 s simulation, including')
    print('  when no batch exists -- so the "97.6%% of epochs oversubscribed" figure')
    print('  was a statistics-scope error on my part, not 2.93 s of real oversend.')
