cd /work/simulation/experiment/scheme1_sba
echo "=== migrationEnabled actually on? (config + default) ==="
grep -nE "^CBAP_MIGRATION_ENABLE|^CBAP_MIGRATION_RELEASE_RATIO" cr_s3_rho040.txt cr_s3_legacy5050.txt
echo
echo "=== applied rate trajectory of one incast flow (flow 1), rho040 vs legacy ==="
for n in cr_s3_legacy5050 cr_s3_rho040; do
  echo "--- $n  time,current_rate(Mbps)"
  awk -F, 'NR>1 && $2==1 && $1>=1.9999 && $1<=2.004 {printf "  %.6f %.3f\n", $1, $8/1e6}' ${n}_out/selected_flow_timeseries.csv | head -14
done
echo
echo "=== rate_transition.csv: does it log the walk? ==="
head -1 cr_s3_rho040_out/rate_transition.csv
awk -F, 'NR>1 && $0 ~ /,1,/ {print} ' cr_s3_rho040_out/rate_transition.csv | head -5
echo
echo "=== applied_rate_audit: distinct applied rates for batch flows ==="
head -1 cr_s3_rho040_out/applied_rate_audit.csv
wc -l < cr_s3_rho040_out/applied_rate_audit.csv
