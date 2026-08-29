set -u
cd /work/simulation/experiment/scheme1_sba/motivation
export LD_LIBRARY_PATH=/work/simulation/build
name=m2_dcqcn
t0=$(date +%s)
timeout --kill-after=60 14400 /work/simulation/build/scratch/third ${name}.txt > /work/matrix_logs/mot_${name}.log 2>&1
code=$?
t1=$(date +%s)
echo "  exit=$code wall=$((t1-t0))s"
echo "=== simulator errors? ==="
grep -cE "CONFIG_ERROR|assert|terminate|LOG_TRUNCATED" /work/matrix_logs/mot_${name}.log | sed 's/^/  error lines: /'
echo "=== flow completion ==="
awk -F, 'NR>1{n++; if($6==65)bg++; else {inc++; if($13==1)incdone++}} END{
  printf "  rows=%d  incast=%d (done %d)  background rows=%d\n", n, inc, incdone, bg}' ${name}_out/flow_summary.csv
echo "=== PREFLIGHT CHECK 1: per-flow bytes on 84:1 -- do BOTH classes deliver? ==="
awk -F, 'NR>1 && $6==65 {printf "  background: acked=%.3f GB goodput=%.3f Gbps completed=%s\n", $12/1e9, $14/1e9, $13}' ${name}_out/flow_summary.csv
awk -F, 'NR>1 && $6!=65 && $13==1 {n++; s+=$12; g+=$14} END{printf "  incast   : %d flows acked=%.3f GB aggregate=%.3f Gbps\n", n, s/1e9, g/1e9}' ${name}_out/flow_summary.csv
echo "=== PREFLIGHT CHECK 2: queue on 84:1 before vs during the collective ==="
awk -F, 'NR>1{t=$1
  if(t>=1.5 && t<2.0){nb++; qb+=$3}
  if(t>=2.0){nd++; qd+=$3; if($3>mx)mx=$3; e+=$6}}
  END{printf "  queue mean before(1.5-2.0s)=%.0f B  during(>2.0s)=%.0f B  peak=%.0f B  ECN=%d\n", qb/nb, qd/nd, mx, e}' ${name}_out/selected_link_timeseries.csv
echo "=== PREFLIGHT CHECK 3: background throughput before vs during (contention proof) ==="
python3 - <<'PY'
import csv
s=[(float(r['time']),float(r['snd_una'])) for r in csv.DictReader(open('m2_dcqcn_out/selected_flow_timeseries.csv')) if r['flow_id']=='0']
s.sort()
def rate(a,b):
    x=[v for t,v in s if t<=a]; y=[v for t,v in s if t<=b]
    return (y[-1]-x[-1])*8/(b-a)/1e9 if x and y else float('nan')
before=rate(1.5,2.0); during=rate(2.0,2.15)
print('  background: before=%.3f Gbps  during=%.3f Gbps  retention=%.2f%%' % (before, during, during/before*100))
print('  -> %s' % ('CONTENTION CONFIRMED (background pushed down by the incast)' if during < before*0.98 else 'NO CONTENTION - background unaffected'))
PY
