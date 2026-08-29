cd /work/simulation/experiment/scheme1_sba
export LD_LIBRARY_PATH=/work/simulation/build
n=cr_s4_rho040
( timeout --kill-after=60 21600 /work/simulation/build/scratch/third ${n}.txt \
    > /work/matrix_logs/${n}.log 2>&1
  code=$?
  got=$(awk -F, 'NR>1 && $6!=65 && $13==1 {c++} END{print c+0}' ${n}_out/flow_summary.csv 2>/dev/null || echo 0)
  echo "$([ "$code" -eq 0 ] && [ "$got" -eq 64 ] && echo OK || echo FAIL)   $n exit=$code $got/64"
  echo "S4_DONE" )
