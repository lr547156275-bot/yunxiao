set -u
cd /work/simulation/experiment/scheme1_sba
export LD_LIBRARY_PATH=/work/simulation/build
RTT_US=15.2; H_US=15.0; OVERSUB=0.20; DRAIN=0.20
# legacy: frozen config verbatim
n=fx_s3_legacy
sed "s|m_cbapsba_s3_seed2_out/|${n}_out/|g" m_cbapsba_s3_seed2.txt > ${n}.txt
mkdir -p ${n}_out
# credit at target 0.25 RTT
n=fx_s3_t025
sed "s|m_cbapsba_s3_seed2_out/|${n}_out/|g" m_cbapsba_s3_seed2.txt > ${n}.txt
{
  echo "CBAP_DELAY_CREDIT_ENABLE 1"
  echo "CBAP_QUEUE_DELAY_TARGET_US $(python3 -c "print('%.4f'%(0.25*$RTT_US))")"
  echo "CBAP_QUEUE_DELAY_HARD_LIMIT_US $RTT_US"
  echo "CBAP_CREDIT_HORIZON_US $H_US"
  echo "CBAP_MAX_OVERSUB_RATIO $OVERSUB"
  echo "CBAP_MAX_DRAIN_RATIO $DRAIN"
  echo "CBAP_QUEUE_SAFETY_MARGIN_BYTES 0"
  echo "CBAP_DELAY_CREDIT_FILE ${n}_out/delay_credit.csv"
} >> ${n}.txt
mkdir -p ${n}_out
for n in fx_s3_legacy fx_s3_t025; do
  ( timeout --kill-after=60 14400 /work/simulation/build/scratch/third ${n}.txt \
      > /work/matrix_logs/${n}.log 2>&1
    code=$?
    got=$(awk -F, 'NR>1 && $6!=65 && $13==1 {c++} END{print c+0}' ${n}_out/flow_summary.csv 2>/dev/null || echo 0)
    echo "$([ "$code" -eq 0 ] && [ "$got" -eq 64 ] && echo OK || echo FAIL)   $n exit=$code $got/64" ) &
done
wait
echo "TWO_CELLS_DONE"
