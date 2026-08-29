cd /work/simulation/experiment/scheme1_sba
echo "=== rate_transition: ANY rows at all? what reasons exist? ==="
wc -l < cr_s3_rho040_out/rate_transition.csv
awk -F, 'NR>1{print $10}' cr_s3_rho040_out/rate_transition.csv | sort | uniq -c | sort -rn | head
echo
echo "=== rows for flow 1 (any time) ==="
awk -F, 'NR>1 && $4==1 {printf "  t=%.6f old=%.3fM tgt=%.3fM new=%.3fM reason=%s\n",$1/1e9,$7/1e6,$8/1e6,$9/1e6,$10}' cr_s3_rho040_out/rate_transition.csv | head -6
echo
echo "=== per-flow migration target the replan computed: from eta trace new_target/N ==="
awk -F, 'NR==2{printf "  new_target_sum=%.3fG / n=%s = %.3f Mbps per flow\n", $12/1e9, $8, $12/$8/1e6}' cr_s3_rho040_out/eta_feasibility.csv
echo
echo "=== so target==100M==MIN_RATE. Is the walk a no-op because current>=target already? ==="
echo "  admission grant rho040 = 81.25M, target = 100M -> step 0.30 would give ~86.9M, observed 100M"
echo "  admission grant legacy = 15.625M, target = 100M -> step 0.30 would give ~40.9M, observed 100M"
echo
echo "=== check: does the 100M come from minRate clamp at line 2341? ==="
sed -n '2336,2348p' /work/simulation/src/point-to-point/model/rdma-hw.cc
