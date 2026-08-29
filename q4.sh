set -u
cd /work/simulation/experiment/scheme1_sba/motivation
export LD_LIBRARY_PATH=/work/simulation/build
# DIAGNOSTIC ONLY (not a paper cell): move the background flow from pg=0 to
# pg=3 so it lands in an ECN-eligible queue. If pg is the cause, its CNP count
# must become non-zero and its DCQCN rate must move below 10 Gbps.
awk 'NR==1{print; next} {if($1==65) $3=3; print}' m2_flow.txt > diag_pg3_flow.txt
echo "=== diagnostic flow table: background now pg=3 ==="
head -2 diag_pg3_flow.txt | sed 's/^/  /'
sed 's|^FLOW_FILE .*|FLOW_FILE diag_pg3_flow.txt|; s|m2_dcqcn_out/|diag_pg3_out/|g' m2_dcqcn.txt > diag_pg3.txt
mkdir -p diag_pg3_out
timeout --kill-after=60 14400 /work/simulation/build/scratch/third diag_pg3.txt > /work/matrix_logs/diag_pg3.log 2>&1
echo "  exit=$?"
python3 - <<'PY'
import csv
r={x['flow_id']:x for x in csv.DictReader(open('diag_pg3_out/round_summary.csv'))}
b=r.get('0',{})
print('=== background on pg=3 (ECN-eligible queue) ===')
print('  cnp_count      = %s   (was 0 on pg=0)' % b.get('cnp_count'))
print('  start_rate     = %s' % b.get('start_rate'))
print('  minimum_rate   = %s   (was 10000000000 on pg=0)' % b.get('minimum_rate'))
print('  end_rate       = %s' % b.get('end_rate'))
fs=list(csv.DictReader(open('diag_pg3_out/flow_summary.csv')))
inc=[x for x in fs if x['src']!='65' and x['completed']=='1']
print('  incast mean FCT = %.3f ms  (pg0 run: 281.564 ms)' % (sum(float(x['fct']) for x in inc)/len(inc)*1000))
bg=[x for x in fs if x['src']=='65'][0]
print('  background goodput = %.3f Gbps (pg0 run: 7.641)' % (float(bg['flow_goodput'])/1e9))
PY
