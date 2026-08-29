set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== which input files do the motivation configs reference? ==="
grep -hoE "^[A-Z_]+ (s[0-9]_[a-z_]+\.txt|topology\.txt)" motivation/m2_dcqcn.txt | sed 's/^/  /'
echo "=== copy them into motivation/ (read-only inputs, not results) ==="
for f in $(grep -hoE "s[0-9]_[a-z_]+\.txt" motivation/*.txt | sort -u); do
  [ -f "$f" ] && cp -f "$f" motivation/ && echo "  copied $f"
done
echo "=== verify every referenced input now resolves ==="
cd motivation
miss=0
for cfg in m1_dcqcn.txt m2_dcqcn.txt m3_dcqcn.txt; do
  for f in $(grep -hoE "^(TOPOLOGY_FILE|FLOW_FILE|ROUND_SCHEDULE_FILE|CBAP_LINK_FILE|CBAP_PATH_FILE) .*" $cfg | awk '{print $2}'); do
    [ -f "$f" ] || { echo "  MISSING for $cfg: $f"; miss=$((miss+1)); }
  done
done
[ "$miss" -eq 0 ] && echo "  all inputs resolve for m1/m2/m3"
