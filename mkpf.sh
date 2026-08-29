set -u
cd /work/simulation/experiment/scheme1_sba
mk() {  # $1=tag $2=rho
  local n=qc_s3_rho$1
  sed "s|au_s3_rho$1_out/|${n}_out/|g" au_s3_rho$1.txt > ${n}.txt
  {
    echo "CBAP_QUEUE_CONTROLLER_ENABLE 1"
    echo "CBAP_QC_SOFT_FRACTION 0.5"
    echo "CBAP_QC_MAX_BOOST_RATIO 0.30"
    echo "CBAP_QC_H_GUARD_US 175"
    echo "CBAP_QC_APP_HARD_DELAY_US 838.86"
    echo "CBAP_QC_TRACE_FILE ${n}_out/qc_trace.csv"
  } >> ${n}.txt
  mkdir -p ${n}_out
  printf "  %-20s rho=%-7s controller=1\n" "${n}.txt" "$2"
}
mk 090   0.90
mk 09875 0.9875
echo
echo "=== the ONLY differences vs the audit cells must be the 6 controller keys ==="
diff <(grep -v "^CBAP_QUEUE_CONTROLLER_ENABLE\|^CBAP_QC_" qc_s3_rho090.txt | sed 's|qc_s3_rho090_out/|au_s3_rho090_out/|g') au_s3_rho090.txt \
  && echo "  identical apart from the controller keys"
echo
echo "=== frozen params must be unchanged ==="
grep -hE "^MIN_RATE|^KMAX_MAP|^KMIN_MAP|^PMAX_MAP|^BUFFER_SIZE|^PAUSE_TIME|^USE_DYNAMIC_PFC|^SIM_SEED|^FLOW_FILE|^TOPOLOGY_FILE|^CBAP_INITIAL_RELEASE_RATIO|^CBAP_DELAY_CREDIT_ENABLE" qc_s3_rho090.txt
