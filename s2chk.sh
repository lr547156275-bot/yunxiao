set -u
D=/work/simulation/experiment/scheme1_sba/m_cbapsba_s2_seed2_out
L=/work/matrix_logs
echo "=== S2 CBAP-SBA: 64 flows, floor 6.4G, bg cap 8G -> theory eta_feasible=(6.4-2.0)/8.0=0.550 ==="
awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i; next}
{ n++
  if ($(h["eta_effective"])+0 > $(h["eta_base"])+0+1e-9) {
    raised++
    printf "  RAISED: eta_base=%s -> eta_feasible=%s eta_eff=%s  N=%s R_old=%.3fG sum=%.3fG/%.0fG\n",
      $(h["eta_base"]), $(h["eta_feasible"]), $(h["eta_effective"]),
      $(h["new_flow_count"]), $(h["r_old_bps"])/1e9,
      $(h["final_sum_target_bps"])/1e9, $(h["link_capacity_bps"])/1e9
  }
  if ($(h["final_sum_target_bps"])+0 > $(h["link_capacity_bps"])+0) infeas++
}
END{printf "  rows=%d  raised=%d  infeasible=%d\n", n, raised+0, infeas+0}' $D/eta_feasibility.csv

echo
echo "=== S2 five algorithms: FCT + queue + ECN ==="
for a in dcqcn dctcp timely hpcc cbapsba; do
  d=/work/simulation/experiment/scheme1_sba/m_${a}_s2_seed2_out
  printf "  %-8s " "$a"
  awk -F, 'NR>1 && $6!=65 && $13==1 {n++; s+=$11; a[n]=$11} END{
    for(i=1;i<=n;i++)for(j=i+1;j<=n;j++)if(a[j]<a[i]){t=a[i];a[i]=a[j];a[j]=t}
    printf "n=%2d mean=%8.3f p99=%8.3f  ", n, s/n*1000, a[int(n*0.99+0.999)]*1000}' $d/flow_summary.csv
  awk -F, 'NR>1 && $1>=1.9{n++; q+=$3; if($3>mx)mx=$3; e+=$6; p+=$8} END{printf "qmean=%7.0f qpeak=%7.0f ecn=%5d pfc=%d\n", q/n, mx, e, p}' $d/selected_link_timeseries.csv
done
echo
echo "=== pre-freeze S2 reference: cbapsba p99 22.773 / queue p99 1261792 / ECN active ==="
