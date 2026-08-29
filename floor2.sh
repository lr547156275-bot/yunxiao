cd /work/simulation/experiment/scheme1_sba
echo "=== audit row: is the floor clamping? (last epoch with 64 flows) ==="
awk -F, 'NR==1{next} $8>0 {print "epoch="$2" legacy_floor="$11/1e6"M below_floor="$12" clamp_count="$13" clamp_delta="$14/1e6"M planner_sum="$6/1e9"G target_sum="$7/1e9"G applied_sum="$8/1e9"G"}' cr_s3_rho040_out/applied_rate_audit.csv | head -4
echo
echo "=== is EvaluateCbapSbaMigration even reached? add up: MIN_RATE and epoch ==="
grep -nE "^MIN_RATE|^CBAP_CONTROL_EPOCH|^CBAP_MAX_WIRE" cr_s3_rho040.txt
echo
echo "=== rate_transition rows for flow 1 around admission ==="
awk -F, 'NR>1 && $4==1 && $1>=1999900000 && $1<=2000200000 {printf "  t=%.6f epoch=%s ph=%s->%s old=%.3fM tgt=%.3fM new=%.3fM reason=%s\n", $1/1e9,$2,$5,$6,$7/1e6,$8/1e6,$9/1e6,$10}' cr_s3_rho040_out/rate_transition.csv | head -8
