cd /work/simulation/experiment/scheme1_sba
echo "=== driver log ==="; cat /work/matrix_logs/core_driver.log 2>/dev/null
for n in cr_s3_legacy5050 cr_s3_rho000 cr_s3_rho040 cr_s3_rho060; do
  printf "  %-20s" $n
  if [ -f ${n}_out/flow_summary.csv ]; then
    awk -F, 'NR>1 && $6!=65 && $13==1{c++} END{printf " %d/64", c+0}' ${n}_out/flow_summary.csv
  else printf " pending"; fi
  echo
done
echo "=== output files present (rho040) ==="
ls cr_s3_rho040_out/ 2>/dev/null | head -20
echo "=== sba_events header ==="
head -1 cr_s3_rho040_out/sba_events.csv 2>/dev/null
echo "=== eta_feasibility header ==="
head -1 cr_s3_rho040_out/eta_feasibility.csv 2>/dev/null
