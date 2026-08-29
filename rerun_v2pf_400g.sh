#!/bin/bash
# Rerun after the u64 fix: fresh byte-regression (binary changed), then the
# two 400G cells that failed on the uint32 overflow.
set -u
export LD_LIBRARY_PATH=/work/simulation/build:${LD_LIBRARY_PATH:-}
BIN=/work/simulation/build/scratch/third
LG=/work/v2_400g/logs
cd /work/simulation/experiment/scheme1_sba
rm -rf regv2_b040_out && mkdir -p regv2_b040_out
timeout -k 60 7200 "$BIN" regv2_b040.txt > "$LG/regv2_b040.log" 2>&1 || { echo REG_RUN_FAIL; exit 3; }
bad=0
for f in flow_summary.csv selected_link_timeseries.csv rate_transition.csv round_summary.csv pfc_events.csv flow_timing.csv; do
  a=$(sha256sum scr8_b040_out/$f | cut -c1-16); b=$(sha256sum regv2_b040_out/$f | cut -c1-16)
  [ "$a" = "$b" ] && echo "  identical $f" || { echo "  DIFFERS $f"; bad=1; }
done
[ $bad -ne 0 ] && { echo "U64_FIX_NOT_INERT -- STOP"; exit 4; }
echo "REGRESSION OK (u64 + domain flag both inert at flag-off)"
cd /work/v2_400g/configs
for tag in pf_burst_400g heff_400g; do
  out=/work/v2_400g/results/$tag
  rm -f "$out/DONE"; mkdir -p "$out"
  echo "RUN $tag $(date '+%H:%M:%S')"
  s=$(date +%s)
  timeout -k 60 7200 "$BIN" "$tag.txt" > "$LG/$tag.log" 2>&1
  rc=$?; e=$(date +%s)
  if [ $rc -eq 0 ] && [ -s "$out/flow_summary.csv" ]; then
    echo "$rc $((e-s))" > "$out/DONE"; echo "OK  $tag $((e-s))s"
  else
    echo "FAIL $tag rc=$rc"; tail -3 "$LG/$tag.log"
  fi
done
echo "=== 400g rerun complete ==="
