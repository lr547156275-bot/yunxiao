cd /work/simulation/experiment/scheme1_sba
echo "=== 1ms: configured, or first-feedback-driven? ==="
grep -nE "CBAP_(MIGRATION|STARTUP|HANDOFF|REPLAN)[A-Z_]*" cr_s3_rho040.txt
echo
echo "=== does 1ms appear as a constant in the source? ==="
grep -rnE "1000000\b|MilliSeconds\(1\)|1e6" /work/simulation/src/point-to-point/model/rdma-hw.cc \
  | grep -iE "migrat|handoff|startup|replan|feedback" | head -10
echo
echo "=== first_feedback_time distribution (col 11) vs release (col 3) ==="
awk -F, 'NR>1 && $8 ~ /DCQCN_OWNED/ {print $3, $11}' cr_s3_rho040_out/sba_events.csv | head -3
echo
echo "=== replan epoch timestamps: when does migration actually apply? ==="
awk -F, 'NR>1{printf "  t=%.6f s  eta_eff=%s  r_old=%.3fG  n=%s  old_tgt=%.3fG new_tgt=%.3fG\n", $1/1e9, $6, $7/1e9, $8, $11/1e9, $12/1e9}' cr_s3_rho040_out/eta_feasibility.csv
