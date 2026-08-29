set -u
cd /work/simulation/experiment/scheme1_sba
mk() {  # $1=tag  $2=rho
  local n=au_s3_rho$1
  sed "s|m_cbapsba_s3_seed2_out/|${n}_out/|g" m_cbapsba_s3_seed2.txt \
    | grep -v "^CBAP_DELAY_CREDIT\|^CBAP_QUEUE_DELAY\|^CBAP_CREDIT_\|^CBAP_MAX_OVERSUB\|^CBAP_QUEUE_SAFETY" > ${n}.txt
  {
    echo "CBAP_CORE_INITIAL_RELEASE 1"
    echo "CBAP_INITIAL_RELEASE_RATIO $2"
    echo "CBAP_DELAY_CREDIT_ENABLE 0"
    echo "CBAP_ETA_FEASIBILITY_TRACE 1"
    echo "CBAP_ETA_FEASIBILITY_FILE ${n}_out/eta_feasibility.csv"
    echo "CBAP_PFC_AUDIT_FILE ${n}_out/pfc_audit.csv"
    echo "CBAP_MIGRATION_TRACE 1"
  } >> ${n}.txt
  mkdir -p ${n}_out
  printf "  %-18s rho=%s\n" "${n}.txt" "$2"
}
mk 055  0.55
mk 075  0.75
mk 090  0.90
mk 09875 0.9875
echo
echo "=== HPCC control arm, same topology/traffic/seed, bg pg=3 ==="
if [ -f m_hpcc_s3_seed2.txt ]; then
  sed "s|m_hpcc_s3_seed2_out/|au_s3_hpcc_out/|g" m_hpcc_s3_seed2.txt > au_s3_hpcc.txt
  mkdir -p au_s3_hpcc_out
  echo "  au_s3_hpcc.txt from m_hpcc_s3_seed2.txt"
  grep -hE "^CC_MODE|^FLOW_FILE|^TOPOLOGY_FILE|^SIM_SEED|^SIMULATOR_STOP_TIME" au_s3_hpcc.txt
else
  echo "  m_hpcc_s3_seed2.txt NOT FOUND -- listing candidates:"
  ls m_hpcc_s3* 2>/dev/null
fi
echo
echo "=== confirm the 4 CBAP cells differ from frozen S3 ONLY in the new keys ==="
diff <(grep -v "^CBAP_CORE_INITIAL_RELEASE\|^CBAP_INITIAL_RELEASE_RATIO\|^CBAP_DELAY_CREDIT_ENABLE\|^CBAP_ETA_FEASIBILITY\|^CBAP_PFC_AUDIT_FILE\|^CBAP_MIGRATION_TRACE" au_s3_rho055.txt | sed 's|au_s3_rho055_out/|m_cbapsba_s3_seed2_out/|g') \
     <(grep -v "^CBAP_ETA_FEASIBILITY\|^CBAP_MIGRATION_TRACE" m_cbapsba_s3_seed2.txt) \
  && echo "  identical apart from the new keys"
