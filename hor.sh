cd /work/simulation/experiment/scheme1_sba
echo "=== observe -> decision -> sender-effect: what does port_summary give? ==="
awk -F, 'NR>1 && NR<5 {printf "  sample_t=%s delivery_t=%s  lag=%.1f us\n", $1, $2, ($2-$1)/1000}' cr_s3_rho040_out/port_summary.csv
echo
echo "=== epoch + telemetry config ==="
grep -nE "^CBAP_CONTROL_EPOCH_US|^CBAP_TELEMETRY|^CBAP_FEEDBACK|^CBAP_MAX_WIRE" cr_s3_rho040.txt
echo
echo "=== PFC threshold: what is it actually? ==="
grep -nE "^BUFFER_SIZE|^USE_DYNAMIC_PFC|^PAUSE_TIME|^KMAX_MAP|^KMIN_MAP" cr_s3_rho040.txt
grep -nE "ecnThresholdBytes|pfcThreshold|GetPfcThreshold|m_pause_time" /work/simulation/src/point-to-point/model/switch-mmu.cc | head -8
echo
echo "=== cbap link file: qmax/ecn threshold used by the controller ==="
f=$(grep -h "^CBAP_LINK_FILE" cr_s3_rho040.txt | awk '{print $2}'); echo "  file=$f"; cat "$f"
