cd /work/simulation/experiment/scheme1_sba
echo "=== (3) FIRST-BATCH DATA per-flow rate, measured from trace ==="
printf "  %-10s %-12s %-14s %-14s %-12s %s\n" rho grant_Mbps first_rate_Mbps eff_rho R_new_G note
for t in 055:0.55 075:0.75 090:0.90 09875:0.9875; do
  tag=${t%%:*}; rho=${t##*:}; n=au_s3_rho$tag
  # grant at admission from sba_events, batch 1 only
  read cnt gsum <<< $(awk -F, '/COLLECTING->STARTUP_SENDING/ && $1!=0 {n++; s+=$6} END{print n+0, s+0}' ${n}_out/sba_events.csv)
  per=$(python3 -c "print('%.4f'%($gsum/$cnt/1e6))" 2>/dev/null)
  newg=$(python3 -c "print('%.4f'%($gsum/1e9))")
  eff=$(python3 -c "print('%.6f'%((8e9-(10e9-$gsum))/8e9))")
  # first observed applied rate of flow 1 at/after release
  fr=$(awk -F, 'NR>1 && $2==1 && $8>0 && $1>=1.9999 {printf "%.4f", $8/1e6; exit}' ${n}_out/selected_flow_timeseries.csv)
  printf "  %-10s %-12s %-14s %-14s %-12s n=%s\n" "$rho" "$per" "$fr" "$eff" "$newg" "$cnt"
done
echo
echo "=== expected per spec: 100.0000 / 125.0000 / 143.7500 / 154.6875 ==="
echo
echo "=== (3b) requested vs effective rho: any MIN_RATE clamping? ==="
for t in 055 075 090 09875; do
  n=au_s3_rho$t
  printf "  %-18s per-flow grants distinct: " $n
  awk -F, '/COLLECTING->STARTUP_SENDING/ && $1!=0 {printf "%.4f\n", $6/1e6}' ${n}_out/sba_events.csv | sort -un | tr '\n' ' '
  echo
done
