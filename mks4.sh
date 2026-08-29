cd /work/simulation/experiment/scheme1_sba
n=cr_s4_rho040
sed "s|m_cbapsba_s4_seed2_out/|${n}_out/|g" m_cbapsba_s4_seed2.txt \
  | grep -v "^CBAP_DELAY_CREDIT\|^CBAP_QUEUE_DELAY\|^CBAP_CREDIT_\|^CBAP_MAX_OVERSUB\|^CBAP_QUEUE_SAFETY" > ${n}.txt
{
  echo "CBAP_CORE_INITIAL_RELEASE 1"
  echo "CBAP_INITIAL_RELEASE_RATIO 0.4"
  echo "CBAP_DELAY_CREDIT_ENABLE 0"
  echo "CBAP_ETA_FEASIBILITY_TRACE 1"
  echo "CBAP_ETA_FEASIBILITY_FILE ${n}_out/eta_feasibility.csv"
} >> ${n}.txt
mkdir -p ${n}_out
echo "=== S4 config diff vs frozen (excluding new keys) ==="
diff <(grep -v "^CBAP_CORE_INITIAL_RELEASE\|^CBAP_INITIAL_RELEASE_RATIO\|^CBAP_DELAY_CREDIT_ENABLE\|^CBAP_ETA_FEASIBILITY" ${n}.txt | sed "s|${n}_out/|m_cbapsba_s4_seed2_out/|g") \
     <(grep -v "^CBAP_ETA_FEASIBILITY" m_cbapsba_s4_seed2.txt) \
  && echo "  identical apart from the new keys"
echo "=== S4 key params (bg cap differs from S3: 9.5G) ==="
grep -E "APP_RATE_CAP_BPS|SIMULATOR_STOP_TIME|APP_RATE_CAP_FLOW" ${n}.txt
