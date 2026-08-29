set -u
cd /work/simulation/experiment/scheme1_sba
export LD_LIBRARY_PATH=/work/simulation/build
echo "third  : $(sha256sum /work/simulation/build/scratch/third | cut -c1-16)"
echo "libns3 : $(sha256sum /work/simulation/build/libns3.18-point-to-point-debug.so | cut -c1-16)"
# ensure all four S3 cells carry the trace keys
for t in 055 075 090 09875; do
  n=au_s3_rho$t
  grep -q "^CBAP_ACTUATION_FILE" ${n}.txt || {
    echo "CBAP_PFC_PORTS_FILE ${n}_out/pfc_ports.csv" >> ${n}.txt
    echo "CBAP_ACTUATION_FILE ${n}_out/actuation.csv" >> ${n}.txt
  }
done
# S4 rho=0.90, valid point (S4 interval [0.6210526, 0.9894737])
n=au_s4_rho090
if [ ! -f ${n}.txt ]; then
  sed "s|m_cbapsba_s4_seed2_out/|${n}_out/|g" m_cbapsba_s4_seed2.txt \
    | grep -v "^CBAP_DELAY_CREDIT\|^CBAP_QUEUE_DELAY\|^CBAP_CREDIT_\|^CBAP_MAX_OVERSUB\|^CBAP_QUEUE_SAFETY" > ${n}.txt
  {
    echo "CBAP_CORE_INITIAL_RELEASE 1"
    echo "CBAP_INITIAL_RELEASE_RATIO 0.90"
    echo "CBAP_DELAY_CREDIT_ENABLE 0"
    echo "CBAP_ETA_FEASIBILITY_TRACE 1"
    echo "CBAP_ETA_FEASIBILITY_FILE ${n}_out/eta_feasibility.csv"
    echo "CBAP_PFC_AUDIT_FILE ${n}_out/pfc_audit.csv"
    echo "CBAP_PFC_PORTS_FILE ${n}_out/pfc_ports.csv"
    echo "CBAP_ACTUATION_FILE ${n}_out/actuation.csv"
    echo "CBAP_MIGRATION_TRACE 1"
  } >> ${n}.txt
  mkdir -p ${n}_out
fi
wave() {
  for n in "$@"; do
    ( timeout --kill-after=60 21600 /work/simulation/build/scratch/third ${n}.txt \
        > /work/matrix_logs/${n}.log 2>&1
      code=$?
      got=$(awk -F, 'NR>1 && $6!=65 && $13==1 {c++} END{print c+0}' ${n}_out/flow_summary.csv 2>/dev/null || echo 0)
      echo "$([ "$code" -eq 0 ] && [ "$got" -eq 64 ] && echo OK || echo FAIL)   $n exit=$code $got/64" ) &
  done
  wait
}
wave au_s3_rho055 au_s3_rho075
wave au_s3_rho090 au_s3_rho09875
wave au_s4_rho090
echo "HEFF5_DONE"
