set -u
cd /work/simulation/experiment/scheme1_sba
export LD_LIBRARY_PATH=/work/simulation/build
# Step 5: one DCQCN and one CBAP-SBA preflight on S3. Algorithm, parameters,
# seed and scenario unchanged -- the ONLY difference from the frozen run is the
# background flow's pg. Written to pf_* so no frozen output is overwritten.
for algo in dcqcn cbapsba; do
  src=m_${algo}_s3_seed2.txt
  name=pf_${algo}_s3
  sed "s|m_${algo}_s3_seed2_out/|${name}_out/|g" "$src" > ${name}.txt
  mkdir -p ${name}_out
  t0=$(date +%s)
  timeout --kill-after=60 14400 /work/simulation/build/scratch/third ${name}.txt > /work/matrix_logs/${name}.log 2>&1
  code=$?; t1=$(date +%s)
  echo "=== $algo: exit=$code wall=$((t1-t0))s ==="
  grep -cE "CONFIG_ERROR|assert|terminate" /work/matrix_logs/${name}.log | sed 's/^/  error lines: /'
  python3 - "$name" <<'PY'
import csv,sys,os
n=sys.argv[1]; d=n+'_out'
fs=list(csv.DictReader(open(os.path.join(d,'flow_summary.csv'))))
inc=[r for r in fs if r['src']!='65' and r['completed']=='1']
bg=[r for r in fs if r['src']=='65'][0]
fct=sorted(float(r['fct'])*1000 for r in inc)
print('  incast %d/64  mean=%.3f ms  p99=%.3f ms  agg=%.3f Gbps'
      % (len(inc), sum(fct)/len(fct), fct[int(len(fct)*0.99+0.999)-1],
         sum(float(r['flow_goodput']) for r in inc)/1e9))
print('  background: acked=%.3f GB goodput=%.3f Gbps completed=%s'
      % (float(bg['acked_bytes'])/1e9, float(bg['flow_goodput'])/1e9, bg['completed']))
rs=os.path.join(d,'round_summary.csv')
if os.path.exists(rs):
    r={x['flow_id']:x for x in csv.DictReader(open(rs))}
    b=r.get('0',{})
    print('  background cnp_count=%s  min_rate=%s  (pg=3 now -> must be >0 / <10G)'
          % (b.get('cnp_count'), b.get('minimum_rate')))
ts=list(csv.DictReader(open(os.path.join(d,'selected_link_timeseries.csv'))))
last=max(float(r['finish_time']) for r in inc)
w=[r for r in ts if 1.9<=float(r['time'])<=last]
q=[float(r['queue_bytes']) for r in w]
print('  queue mean=%.0f peak=%.0f  ECN=%.0f  PFC=%.0f'
      % (sum(q)/len(q), max(q), sum(float(r['ecn_marks_delta']) for r in ts),
         sum(float(r['pfc_event_delta']) for r in ts)))
PY
done
