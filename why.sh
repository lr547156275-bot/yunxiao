cd /work/simulation/experiment/scheme1_sba
echo "=== are the flow_summary files literally identical? ==="
md5sum cr_s3_legacy5050_out/flow_summary.csv cr_s3_rho000_out/flow_summary.csv \
       cr_s3_rho040_out/flow_summary.csv cr_s3_rho060_out/flow_summary.csv
echo
echo "=== how long does a flow stay at the SBA rate before handoff? ==="
for n in cr_s3_legacy5050 cr_s3_rho040; do
  echo "--- $n"
  awk -F, 'NR>1 && $8 ~ /STARTUP_SENDING->DCQCN_OWNED/ {print $11-$3}' ${n}_out/sba_events.csv \
    | sort -n | awk '{a[NR]=$1} END{printf "  handoff delay ns: min=%d median=%d max=%d  (n=%d)\n", a[1], a[int(NR/2)], a[NR], NR}'
done
echo
echo "=== rate right after handoff vs SBA grant ==="
for n in cr_s3_legacy5050 cr_s3_rho040; do
  printf "  %-18s handoff_rate distinct: " $n
  awk -F, 'NR>1 && $8 ~ /DCQCN_OWNED/ {printf "%.3f ", $12/1e6}' ${n}_out/sba_events.csv | tr ' ' '\n' | sort -un | tr '\n' ' '
  echo
done
echo
echo "=== when does the batch actually reach line rate? (first 12 samples in batch) ==="
for n in cr_s3_legacy5050 cr_s3_rho040; do
  echo "--- $n  time,util,queue"
  awk -F, 'NR>1 && $1>=2.0 && $1<=2.0012 {printf "  %.5f %.4f %d\n", $1, $4, $3}' ${n}_out/selected_link_timeseries.csv | head -12
done
