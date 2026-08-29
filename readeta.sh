set -u
D=/work/simulation/experiment/scheme1_sba/g_cbapsba_s3_seed2_out
echo "=== eta_feasibility.csv (all rows) ==="
column -s, -t $D/eta_feasibility.csv 2>/dev/null | cut -c1-200
echo
echo "=== acceptance checks on the trace ==="
awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i; next}
{
  n++
  eb=$(h["eta_base"])+0; ef=$(h["eta_feasible"])+0; ee=$(h["eta_effective"])+0
  want = (ef>eb ? ef : eb)
  if (want>1) want=1
  if ((ee-want)>1e-6 || (want-ee)>1e-6) bad_eta++
  fs=$(h["final_sum_target_bps"])+0; C=$(h["link_capacity_bps"])+0
  if (fs>C) bad_cap++
  if ($(h["feasible"])+0 != 1) notfeas++
}
END{
  printf "  rows=%d\n", n
  printf "  eta_effective == max(eta_base, eta_feasible) : %s (%d violations)\n", (bad_eta?"FAIL":"PASS"), bad_eta+0
  printf "  final_sum_target <= link_capacity            : %s (%d violations)\n", (bad_cap?"FAIL":"PASS"), bad_cap+0
  printf "  feasible flag == 1 on every row              : %s (%d rows not feasible)\n", (notfeas?"FAIL":"PASS"), notfeas+0
}' $D/eta_feasibility.csv
