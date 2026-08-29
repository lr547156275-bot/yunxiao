set -u
cd /work/simulation/experiment/scheme1_sba
for f in s1_trace.txt s3_trace.txt s4_trace.txt; do
  [ -f "$f" ] && cp -f "$f" motivation/ && echo "  copied $f"
done
cd motivation
echo "=== full input resolution check for all 7 configs ==="
miss=0
for cfg in m1_dcqcn.txt m1_dctcp.txt m1_timely.txt m2_dcqcn.txt m2_hpcc.txt m3_dcqcn.txt m3_hpcc.txt; do
  for f in $(grep -hoE "^(TOPOLOGY_FILE|FLOW_FILE|TRACE_FILE|ROUND_SCHEDULE_FILE|CBAP_LINK_FILE|CBAP_PATH_FILE) .*" $cfg | awk '{print $2}'); do
    [ -f "$f" ] || { echo "  MISSING $cfg -> $f"; miss=$((miss+1)); }
  done
done
[ "$miss" -eq 0 ] && echo "  all inputs resolve for all 7 configs"
