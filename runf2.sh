set -u
cd /work/simulation/experiment/scheme1_sba
export LD_LIBRARY_PATH=/work/simulation/build
for tag in s3 s4; do
  name=f_cbapsba_${tag}_seed2
  if [ -f /work/matrix_logs/${name}.done ]; then echo "SKIP $name"; continue; fi
  rm -f /work/matrix_logs/${name}.done
  t0=$(date +%s)
  timeout --kill-after=60 14400 /work/simulation/build/scratch/third "${name}.txt" \
      > /work/matrix_logs/${name}.log 2>&1
  code=$?
  t1=$(date +%s)
  got=$(awk -F, 'NR>1 && $6 != 65 && $13 == 1 {n++} END{print n+0}' ${name}_out/flow_summary.csv 2>/dev/null || echo 0)
  last=$(awk -F, 'NR>1{t=$1} END{printf "%.4f", t+0}' ${name}_out/selected_link_timeseries.csv 2>/dev/null || echo 0)
  echo "$tag: exit=$code incast_completed=$got/64 last_trace_t=$last wall=$((t1-t0))s"
  if [ "$code" -eq 0 ] && [ "$got" -eq 64 ]; then touch /work/matrix_logs/${name}.done; echo "  OK"; else echo "  CHECK"; fi
done
echo "ALL_DONE"
