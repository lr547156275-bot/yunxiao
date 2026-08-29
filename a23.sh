set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== Q2/Q3: the eta trace from the corrected S3 run (ground truth) ==="
column -s, -t m_cbapsba_s3_seed2_out/eta_feasibility.csv 2>/dev/null | cut -c1-150 | head -4
echo
echo "=== Q2: was sum(target) EVER above capacity, in any cell? ==="
tot=0; viol=0
for t in s1 s2 s3 s6 s4 s5; do
  f=m_cbapsba_${t}_seed2_out/eta_feasibility.csv
  [ -f "$f" ] || continue
  r=$(awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i;next}{n++; if($(h["final_sum_target_bps"])+0 > $(h["link_capacity_bps"])+0) v++} END{printf "%d %d", n+0, v+0}' "$f")
  set -- $r; tot=$((tot+$1)); viol=$((viol+$2))
  printf "  %-3s replans=%-4s violations=%s\n" "$t" "$1" "$2"
done
echo "  TOTAL: $tot replans, $viol violations of sum(target) <= C"
echo
echo "=== Q3: the actual per-flow target at handover (S3) ==="
awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i;next} NR==2{
  printf "  R_old=%.3f G  N=%s  eta_base=%s eta_feasible=%s eta_eff=%s\n", $(h["r_old_bps"])/1e9, $(h["new_flow_count"]), $(h["eta_base"]), $(h["eta_feasible"]), $(h["eta_effective"])
  printf "  oldShare=%.3f G   newShare(sum)=%.3f G   per-flow=%.3f Mbps\n", $(h["old_target_sum_bps"])/1e9, $(h["new_target_sum_bps"])/1e9, $(h["new_target_sum_bps"])/$(h["new_flow_count"])/1e6
  printf "  final_sum=%.3f G / C=%.0f G   floor_binding=%s\n", $(h["final_sum_target_bps"])/1e9, $(h["link_capacity_bps"])/1e9, $(h["floor_binding"])
}' m_cbapsba_s3_seed2_out/eta_feasibility.csv
echo
echo "=== measured outcome: does 6.1G/3.2G match the plan? ==="
awk -F, 'NR>1 && $6!=65 && $13==1 {n++; s+=$14} END{printf "  incast delivered: %d flows, %.3f Gbps aggregate (%.1f Mbps/flow)\n", n, s/1e9, s/n/1e6}' m_cbapsba_s3_seed2_out/flow_summary.csv
