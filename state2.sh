echo "=== nothing running? ==="
ps -eo etime,cmd | grep "[t]hird " | head -5 || echo "  none"
echo "=== logs retained ==="
ls -la /work/matrix_logs/preflight_driver.log /work/matrix_logs/qc_s3_rho090.log 2>/dev/null | awk '{print "  "$5" "$NF}'
ls /work/simulation/experiment/scheme1_sba/qc_s3_rho090_out/qc_trace.csv 2>/dev/null | sed 's/^/  kept: /'
echo "=== frozen guards ==="
cd /work/simulation/experiment/scheme1_sba
grep -hE "^MIN_RATE|^CBAP_DELAY_CREDIT_ENABLE|^SIM_SEED|^KMIN_MAP|^BUFFER_SIZE" qc_s3_rho090.txt
grep -hE "^CBAP_QC_SOFT_FRACTION|^CBAP_QC_MAX_BOOST_RATIO|^CBAP_QC_H_GUARD_US|^CBAP_QC_SAFETY_MARGIN_BYTES|^CBAP_INITIAL_RELEASE_RATIO" qc_s3_rho090.txt
echo "  controller flag default in source: $(grep -c 'cbap_queue_controller_enable = 0' /work/simulation/scratch/third.cc)"
