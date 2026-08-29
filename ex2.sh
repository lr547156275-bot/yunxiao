cd /work/simulation/experiment/scheme1_sba
echo "=== applied-rate trajectory of flow 1 across release, all four rho ==="
for t in 055 075 090 09875; do
  n=au_s3_rho$t
  echo "--- $n"
  awk -F, 'NR>1 && $2==1 && $1>=1.99998 && $1<=2.00012 {printf "  t=%.6f phase=%-14s rate=%.4f Mbps\n", $1, $4, $8/1e6}' ${n}_out/selected_flow_timeseries.csv | head -9
done
echo
echo "=== release time from sba_events (batch 1) ==="
awk -F, 'NR>1 && $1!=0 {print "  release_time_ns="$3; exit}' au_s3_rho055_out/sba_events.csv
