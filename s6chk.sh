set -u
L=/work/matrix_logs
D=/work/simulation/experiment/scheme1_sba
echo "=== s6 done so far ==="
ls $L/m_*_s6_seed2.done 2>/dev/null | xargs -n1 basename 2>/dev/null | sed 's/^/  /'
echo "=== running ==="
pgrep -a -x third 2>/dev/null | grep -oE "m_[a-z]+_s[0-9]_seed2" | sed 's/^/  /' || echo "  none"
if [ -f $D/m_cbapsba_s6_seed2_out/eta_feasibility.csv ]; then
  echo
  echo "=== S6 CBAP-SBA eta trace: PER-LINK test ==="
  echo "    S6 = dual bottleneck, 30+31 flows. per-link floor 3.0-3.1G < 10G -> expect NO raise."
  echo "    If N were taken globally (60 flows, 6.0G floor) it would WRONGLY raise."
  awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i; next}
  { n++
    printf "  link=%s N=%-3s R_old=%.3fG eta_base=%s eta_feasible=%9s eta_eff=%s sum=%.3fG/%.0fG %s\n",
      $(h["link_id"]), $(h["new_flow_count"]), $(h["r_old_bps"])/1e9,
      $(h["eta_base"]), $(h["eta_feasible"]), $(h["eta_effective"]),
      $(h["final_sum_target_bps"])/1e9, $(h["link_capacity_bps"])/1e9,
      ($(h["feasible"])==1?"ok":"INFEASIBLE")
    if ($(h["eta_effective"])+0 > $(h["eta_base"])+0+1e-9) raised++
  }
  END{printf "\n  rows=%d  raised=%d  (expected 0 if per-link N is correct)\n", n, raised+0}' \
    $D/m_cbapsba_s6_seed2_out/eta_feasibility.csv
else
  echo "  (cbapsba s6 not finished yet)"
fi
