set -u
cd /work/simulation/experiment/scheme1_sba
export LD_LIBRARY_PATH=/work/simulation/build
run_pair() {
  for n in "$1" "$2"; do
    [ -f /work/matrix_logs/${n}.done ] && { echo "SKIP $n"; continue; }
    ( timeout --kill-after=60 14400 /work/simulation/build/scratch/third ${n}.txt \
        > /work/matrix_logs/${n}.log 2>&1
      code=$?
      got=$(awk -F, 'NR>1 && $6!=65 && $13==1 {c++} END{print c+0}' ${n}_out/flow_summary.csv 2>/dev/null || echo 0)
      if [ "$code" -eq 0 ] && [ "$got" -eq 64 ]; then touch /work/matrix_logs/${n}.done; echo "OK   $n ($got/64)"; else echo "FAIL $n (exit=$code $got/64)"; fi
    ) &
  done
  wait
}
run_pair qc_s3_legacy qc_s3_t025
run_pair qc_s3_t050  qc_s3_t080
run_pair qc_s4_legacy qc_s4_t025
run_pair qc_s4_t050  qc_s4_t080
echo "PREFLIGHT_8_DONE done=$(ls /work/matrix_logs/qc_s[34]_*.done 2>/dev/null | wc -l)/8"
