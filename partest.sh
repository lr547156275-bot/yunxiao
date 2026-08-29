set -u
cd /work/simulation/experiment/scheme1_sba
export LD_LIBRARY_PATH=/work/simulation/build
# Throwaway parallel probe on S2 (8 min serial each) using scratch names so
# nothing in the real matrix is touched. Runs AFTER the current cell finishes
# to avoid a 3-way fight.
for tag in s2; do
  for a in dctcp timely; do
    src=m_${a}_${tag}_seed2.txt
    [ -f "$src" ] || { echo "  missing $src (matrix has not built it yet)"; exit 0; }
    sed "s|m_${a}_${tag}_seed2_out/|PARTEST_${a}_out/|g" "$src" > PARTEST_${a}.txt
    mkdir -p PARTEST_${a}_out
  done
done
echo "=== launching 2 cells concurrently ==="
t0=$(date +%s)
( /work/simulation/build/scratch/third PARTEST_dctcp.txt > /tmp/pt_dctcp.log 2>&1 ) &
p1=$!
( /work/simulation/build/scratch/third PARTEST_timely.txt > /tmp/pt_timely.log 2>&1 ) &
p2=$!
wait $p1 $p2
t1=$(date +%s)
echo "  2 cells in parallel: $((t1-t0))s wall"
echo "  serial reference (pre-freeze manifests): dctcp=$(awk -F= '$1=="wall_seconds"{print $2}' /work/matrix_logs/pre_freeze_run/m_dctcp_s2_seed2.manifest)s + timely=$(awk -F= '$1=="wall_seconds"{print $2}' /work/matrix_logs/pre_freeze_run/m_timely_s2_seed2.manifest)s"
echo "=== did both complete correctly? ==="
for a in dctcp timely; do
  n=$(awk -F, 'NR>1 && $6!=65 && $13==1 {c++} END{print c+0}' PARTEST_${a}_out/flow_summary.csv 2>/dev/null || echo 0)
  echo "  $a: incast=$n/64"
done
