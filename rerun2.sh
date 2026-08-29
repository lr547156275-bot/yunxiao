set -u
cd /work/simulation/experiment/scheme1_sba
export LD_LIBRARY_PATH=/work/simulation/build
echo "third  : $(sha256sum /work/simulation/build/scratch/third | cut -c1-16)"
echo "libns3 : $(sha256sum /work/simulation/build/libns3.18-point-to-point-debug.so | cut -c1-16)"
for t in 055 075 090 09875; do
  n=au_s3_rho$t
  grep -q "^CBAP_PFC_PORTS_FILE" ${n}.txt || {
    echo "CBAP_PFC_PORTS_FILE ${n}_out/pfc_ports.csv" >> ${n}.txt
    echo "CBAP_ACTUATION_FILE ${n}_out/actuation.csv" >> ${n}.txt
  }
done
pair() {
  for n in "$@"; do
    ( timeout --kill-after=60 14400 /work/simulation/build/scratch/third ${n}.txt \
        > /work/matrix_logs/${n}.log 2>&1
      code=$?
      got=$(awk -F, 'NR>1 && $6!=65 && $13==1 {c++} END{print c+0}' ${n}_out/flow_summary.csv 2>/dev/null || echo 0)
      echo "$([ "$code" -eq 0 ] && [ "$got" -eq 64 ] && echo OK || echo FAIL)   $n exit=$code $got/64" ) &
  done
  wait
}
pair au_s3_rho055 au_s3_rho090
pair au_s3_rho075 au_s3_rho09875
echo "AUDIT2_DONE"
