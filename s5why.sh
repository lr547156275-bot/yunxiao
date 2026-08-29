set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== S5 eta trace: 42 rows -- was eta raised, and did it stay feasible? ==="
awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i; next}
{ n++
  if ($(h["eta_effective"])+0 > $(h["eta_base"])+0+1e-9) raised++
  if ($(h["final_sum_target_bps"])+0 > $(h["link_capacity_bps"])+0) infeas++
  if (n<=3 || $(h["eta_effective"])+0 > $(h["eta_base"])+0+1e-9)
    printf "  t=%.4fs N=%-3s R_old=%.3fG eta_f=%9s eta_eff=%s sum=%.3fG/%.0fG floor=%s\n",
      $(h["timestamp_ns"])/1e9, $(h["new_flow_count"]), $(h["r_old_bps"])/1e9,
      $(h["eta_feasible"]), $(h["eta_effective"]),
      $(h["final_sum_target_bps"])/1e9, $(h["link_capacity_bps"])/1e9, $(h["floor_binding"])
}
END{printf "\n  rows=%d raised=%d infeasible=%d\n", n, raised+0, infeas+0}' \
  m_cbapsba_s5_seed2_out/eta_feasibility.csv
echo
echo "=== when does the queue build in S5? (collective runs 1.9 -> ~2.25s) ==="
awk -F, 'NR>1{t=$1; q=$3; e=$6
  if(q>400000 && first==0){first=t}
  if(e>0 && firstecn==0){firstecn=t}
  if(q>mx){mx=q; mxt=t}}
  END{printf "  first queue>KMIN at t=%.4f  first ECN at t=%.4f  peak %.0f at t=%.4f\n", first, firstecn, mx, mxt}' \
  m_cbapsba_s5_seed2_out/selected_link_timeseries.csv
echo "=== incast completion span in S5 ==="
awk -F, 'NR>1 && $6!=65 && $13==1 {if(mn==0||$10<mn)mn=$10; if($10>mx)mx=$10} END{printf "  first finish=%.4f last finish=%.4f (span %.1f ms)\n", mn, mx, (mx-mn)*1000}' \
  m_cbapsba_s5_seed2_out/flow_summary.csv
echo "=== S5 message size vs others ==="
awk 'NR==3{printf "  s5 incast msg = %s B (%.1f MiB)\n", $5, $5/1048576}' s5_flow.txt
