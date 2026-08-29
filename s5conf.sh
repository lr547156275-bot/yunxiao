set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== S5: how long is the collective vs the other scenarios? ==="
for t in s2 s3 s4 s5; do
  awk -F, -v tag="$t" 'NR>1 && $6!=65 && $13==1 {if($10>mx)mx=$10} END{printf "  %-3s last incast finish=%.4f s -> collective spans %.1f ms after release at 1.9\n", tag, mx, (mx-1.9)*1000}' m_cbapsba_${t}_seed2_out/flow_summary.csv
done
echo
echo "=== during the collective, was the per-flow target above MIN_RATE? (floor_binding) ==="
for t in s2 s3 s4 s5; do
  printf "  %-3s floor_binding rows: " "$t"
  awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i; next}{if($(h["floor_binding"])+0==1)b++; n++} END{printf "%d of %d\n", b+0, n}' m_cbapsba_${t}_seed2_out/eta_feasibility.csv
done
echo
echo "=== S5 aggregate demand during the collective: is 64 x target > C? ==="
awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i; next} NR==2{
  printf "  at handover: new_target_sum=%.3f G  old_target_sum=%.3f G  total=%.3f G / %.0f G\n",
    $(h["new_target_sum_bps"])/1e9, $(h["old_target_sum_bps"])/1e9,
    $(h["final_sum_target_bps"])/1e9, $(h["link_capacity_bps"])/1e9
  printf "  per-flow new target = %.3f Mbps (MIN_RATE=%.0f Mbps)\n",
    $(h["new_target_sum_bps"])/$(h["new_flow_count"])/1e6, $(h["min_rate_bps"])/1e6}' \
  m_cbapsba_s5_seed2_out/eta_feasibility.csv
echo
echo "=== S5 actual delivered rate per incast flow ==="
awk -F, 'NR>1 && $6!=65 && $13==1 {n++; s+=$14} END{printf "  mean per-flow goodput=%.3f Mbps  aggregate=%.3f Gbps\n", s/n/1e6, s/1e9}' m_cbapsba_s5_seed2_out/flow_summary.csv
