#!/bin/bash
# v2 preflight + H_eff round: byte-regression first, then 9 cells, serial.
set -u
export LD_LIBRARY_PATH=/work/simulation/build:${LD_LIBRARY_PATH:-}
BIN=/work/simulation/build/scratch/third
LG=/work/v2_400g/logs
mkdir -p "$LG"
cd /work/simulation/experiment/scheme1_sba

# phase 0: v1 byte-identity regression (v2 domain flag defaults OFF)
if [ ! -f regv2_b040_out/DONE ]; then
  sed "s|scr8_b040_out|regv2_b040_out|g" scr8_b040.txt > regv2_b040.txt
  mkdir -p regv2_b040_out
  timeout -k 60 7200 "$BIN" regv2_b040.txt > "$LG/regv2_b040.log" 2>&1 \
    && echo "0 0" > regv2_b040_out/DONE || { echo "REG RUN FAILED"; exit 3; }
fi
bad=0
for f in flow_summary.csv selected_link_timeseries.csv rate_transition.csv \
         round_summary.csv pfc_events.csv flow_timing.csv; do
  a=$(sha256sum scr8_b040_out/$f | cut -c1-16)
  b=$(sha256sum regv2_b040_out/$f | cut -c1-16)
  [ "$a" = "$b" ] && echo "  identical $f" || { echo "  DIFFERS $f"; bad=1; }
done
[ $bad -ne 0 ] && { echo "V2_FLAG_NOT_INERT -- STOP, report"; exit 4; }
echo "REGRESSION OK: flag-off byte-identical"

cd /work/v2_400g/configs
for tag in pf_single_10g pf_single_200g pf_single_400g \
           pf_burst_10g pf_burst_200g pf_burst_400g \
           heff_10g heff_200g heff_400g; do
  out=/work/v2_400g/results/$tag
  [ -f "$out/DONE" ] && { echo "SKIP $tag"; continue; }
  avail=$(df --output=avail /work | tail -1 | tr -d ' ')
  [ "$avail" -lt 1048576 ] && { echo DISK_GUARD_FAIL; exit 2; }
  mkdir -p "$out"
  echo "RUN  $tag $(date '+%H:%M:%S')"
  s=$(date +%s)
  timeout -k 60 7200 "$BIN" "$tag.txt" > "$LG/$tag.log" 2>&1
  rc=$?; e=$(date +%s)
  if [ $rc -eq 0 ] && [ -s "$out/flow_summary.csv" ]; then
    echo "$rc $((e-s))" > "$out/DONE"; echo "OK   $tag $((e-s))s"
  else
    echo "FAIL $tag rc=$rc $((e-s))s"; tail -3 "$LG/$tag.log"
  fi
done
echo "=== v2 preflight round complete $(date) ==="
touch "$LG/PF_ALL_DONE"
