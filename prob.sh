set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== PROBLEM 1: phase=1 (NORMAL) at the very first replan, q=0 ==="
echo "  the latch fires immediately because q=0 <= 19000 BEFORE the burst forms,"
echo "  so the SYNC_BURST allowance is never actually used."
echo
echo "=== PROBLEM 2: q>q_target rows show drain=0 and budget/C=1.0000 ==="
python3 - <<'PY'
import csv
rows=list(csv.DictReader(open('qc_s3_t025_out/delay_credit.csv')))
for r in rows[1:4]:
    q=int(r['queue_bytes']); qt=int(r['q_target_bytes'])
    print('  q=%-7s q_target=%-6s -> drain_bps=%-12s total/C=%s'
          % (q, qt, r['drain_bps'], r['budget_over_capacity']))
print()
print('  q is far above q_target, so the law says DRAIN. But drain=0.')
print('  Cause: these rows are logged from the migration replan, which only runs')
print('  when a handover is in progress; the budget it computed was not applied')
print('  as a drain because link->second (the planner capacity) is used elsewhere.')
PY
echo
echo "=== did it change the outcome vs legacy? ==="
python3 - <<'PY'
import csv
def load(d):
    fs=list(csv.DictReader(open(d+'/flow_summary.csv')))
    ts=list(csv.DictReader(open(d+'/selected_link_timeseries.csv')))
    inc=[r for r in fs if r['src']!='65' and r['completed']=='1']
    fct=sorted(float(r['fct'])*1000 for r in inc)
    last=max(float(r['finish_time']) for r in inc)
    q=[float(r['queue_bytes'] or 0) for r in ts if 1.9<=float(r['time'])<=last]
    return (sum(fct)/len(fct), fct[int(len(fct)*0.99+0.999)-1],
            sum(float(r['flow_goodput']) for r in inc)/1e9,
            sum(q)/len(q), max(q),
            sum(float(r['ecn_marks_delta'] or 0) for r in ts))
l=load('qc_s3_legacy_out'); t=load('qc_s3_t025_out')
print('  %-14s %-12s %-12s %s' % ('metric','legacy','t=0.25RTT','delta'))
for i,n in enumerate(('mean FCT','p99 FCT','goodput','q mean','q peak','ECN')):
    d='%+.3f%%' % ((t[i]-l[i])/l[i]*100) if l[i] else 'n/a'
    print('  %-14s %-12.4f %-12.4f %s' % (n, l[i], t[i], d))
PY
