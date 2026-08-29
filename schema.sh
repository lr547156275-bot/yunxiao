cd /work/simulation/experiment/scheme1_sba/m_cbapsba_s3_seed2_out
for f in flow_summary.csv sba_events.csv selected_link_timeseries.csv port_summary.csv eta_feasibility.csv; do
  echo "--- $f"
  [ -f $f ] && head -1 $f || echo "  (absent)"
done
echo "--- files ---"; ls
