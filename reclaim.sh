set -u
cd /work/simulation/experiment/scheme1_sba
# Remove ONLY the three bulky regenerable trace files from PRE-FREEZE cells.
# Their derived metrics are already in final_report/ and analysis_s*/, and the
# new run overwrites these files anyway (ns-3 opens outputs with "w").
# Named explicitly -- no wildcard directory removal.
freed=0
for d in m_*_seed2_out; do
  [ -d "$d" ] || continue
  for f in qlen.txt selected_flow_timeseries.csv selected_link_timeseries.csv trace_output.txt; do
    if [ -f "$d/$f" ]; then
      sz=$(stat -c %s "$d/$f")
      rm -f "$d/$f"
      freed=$((freed + sz))
    fi
  done
done
printf "  freed %.2f GB from pre-freeze trace files\n" "$(echo "$freed" | awk '{print $1/1073741824}')"
echo "  small analysis CSVs kept:"
ls m_cbapsba_s3_seed2_out/ | head -6 | sed 's/^/    /'
echo
df -h /work | tail -1
