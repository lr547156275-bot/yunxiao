set -u
D=/work/simulation/experiment/scheme1_sba/m_cbapsba_s1_seed2_out
echo "=== S1 CBAP-SBA eta trace: 16 flows, floor = 16 x 100M = 1.6 G < 10 G ==="
echo "    prediction: eta_feasible <= 0 so eta stays at eta_base 0.5 (no intervention)"
if [ -f $D/eta_feasibility.csv ]; then
  awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i; next}
  { n++
    printf "  eta_base=%s eta_feasible=%9s eta_eff=%s  N=%-3s R_old=%.3fG  sum=%.3fG/%.0fG %s\n",
      $(h["eta_base"]), $(h["eta_feasible"]), $(h["eta_effective"]),
      $(h["new_flow_count"]), $(h["r_old_bps"])/1e9,
      $(h["final_sum_target_bps"])/1e9, $(h["link_capacity_bps"])/1e9,
      ($(h["feasible"])==1?"feasible":"INFEASIBLE")
    if ($(h["eta_effective"])+0 > $(h["eta_base"])+0 + 1e-9) raised++
  }
  END{printf "\n  rows=%d  eta raised in %d rows\n", n, raised+0}' $D/eta_feasibility.csv
else
  echo "  eta_feasibility.csv ABSENT"
fi
echo "=== result vs pre-freeze S1 cbapsba (was 5.929 p99, queue p99 10480) ==="
awk -F, 'NR>1 && $6!=65 && $13==1 {n++; s+=$11; a[n]=$11} END{
  for(i=1;i<=n;i++)for(j=i+1;j<=n;j++)if(a[j]<a[i]){t=a[i];a[i]=a[j];a[j]=t}
  printf "  incast=%d/16  mean=%.3f ms  p99=%.3f ms\n", n, s/n*1000, a[int(n*0.99+0.999)]*1000}' $D/flow_summary.csv
awk -F, 'NR>1 && $1>=1.9{n++; q+=$3; if($3>mx)mx=$3; e+=$6} END{printf "  queue mean=%.0f peak=%.0f ecn=%d\n", q/n, mx, e}' $D/selected_link_timeseries.csv
