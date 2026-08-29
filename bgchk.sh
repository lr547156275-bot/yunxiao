set -u
D=/work/simulation/experiment/scheme1_sba
echo "=== 1. is the background flow traced per-flow (needed for throughput/min/recovery)? ==="
for t in s1 s2 s3 s6 s4; do
  f=$D/m_cbapsba_${t}_seed2.txt
  [ -f "$f" ] || continue
  printf "  %-3s ROUND_TRACE_SELECTED_FLOWS=%s  APP_RATE_CAP_FLOW=%s\n" "$t" \
    "$(awk '/^ROUND_TRACE_SELECTED_FLOWS/{print $2}' $f)" \
    "$(awk '/^APP_RATE_CAP_FLOW/{print $2}' $f)"
done
echo
echo "=== 2. does selected_flow_timeseries.csv exist and contain flow 0 (background)? ==="
for t in s1 s2 s3 s6 s4; do
  ts=$D/m_cbapsba_${t}_seed2_out/selected_flow_timeseries.csv
  if [ -f "$ts" ]; then
    printf "  %-3s rows=%-8s flow_ids=[%s]\n" "$t" \
      "$(awk 'END{print NR-1}' $ts)" \
      "$(awk -F, 'NR>1{a[$2]=1} END{s=""; for(k in a) s=s k ","; print substr(s,1,length(s)-1)}' $ts)"
  else
    printf "  %-3s MISSING selected_flow_timeseries.csv\n" "$t"
  fi
done
echo
echo "=== 3. background flow row present in flow_summary (fct/acked/completed)? ==="
for t in s1 s2 s3 s6 s4; do
  fs=$D/m_cbapsba_${t}_seed2_out/flow_summary.csv
  [ -f "$fs" ] || continue
  printf "  %-3s " "$t"
  awk -F, 'NR>1 && ($6==65 || $6==61) {printf "src=%s acked=%.3fGB completed=%s fct=%s | ", $6, $12/1e9, $13, ($11==""?"-":$11)} END{print ""}' $fs
done
