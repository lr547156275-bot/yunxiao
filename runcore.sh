set -u
cd /work/simulation/experiment/scheme1_sba
export LD_LIBRARY_PATH=/work/simulation/build
pair() {
  for n in "$1" "$2"; do
    ( timeout --kill-after=60 14400 /work/simulation/build/scratch/third ${n}.txt \
        > /work/matrix_logs/${n}.log 2>&1
      code=$?
      got=$(awk -F, 'NR>1 && $6!=65 && $13==1 {c++} END{print c+0}' ${n}_out/flow_summary.csv 2>/dev/null || echo 0)
      echo "$([ "$code" -eq 0 ] && [ "$got" -eq 64 ] && echo OK || echo FAIL)   $n exit=$code $got/64" ) &
  done
  wait
}
pair cr_s3_legacy5050 cr_s3_rho000
pair cr_s3_rho040     cr_s3_rho060
echo "CORE_4CELL_DONE"
