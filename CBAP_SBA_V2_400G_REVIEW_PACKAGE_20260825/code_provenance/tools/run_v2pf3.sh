#!/bin/bash
# v2 preflight ROUND 3: twin byte-regression (sha-keyed marker -- reruns
# whenever the binary changes), then all nine cells in three rate lanes in
# parallel, with per-cell RSS sampling, then the analyzer.
set -u
export LD_LIBRARY_PATH=/work/simulation/build:${LD_LIBRARY_PATH:-}
BIN=/work/simulation/build/scratch/third
V2=/work/v2_400g
LG=$V2/logs
CF=$V2/configs
RS=$V2/results

free_gb() { df -BG /work | awk 'NR==2{gsub("G","",$4); print $4}'; }

run_cell() {
  local tag=$1
  local out=$RS/$tag
  if [ "$(free_gb)" -lt 1 ]; then echo "DISK_GUARD_FAIL $tag (cell not started)"; return 9; fi
  mkdir -p "$out"; rm -f "$out/DONE"
  echo "RUN $tag $(date '+%H:%M:%S')"
  local s
  s=$(date +%s)
  timeout -k 60 7200 "$BIN" "$tag.txt" > "$LG/$tag.log" 2>&1 &
  local tpid=$!
  (
    echo "epoch_s,rss_kb" > "$LG/$tag.rss.csv"
    while kill -0 $tpid 2>/dev/null; do
      p=$(pgrep -P $tpid -x third 2>/dev/null | head -1)
      if [ -n "$p" ] && [ -r "/proc/$p/status" ]; then
        r=$(awk '/VmRSS/{print $2}' "/proc/$p/status" 2>/dev/null)
        [ -n "$r" ] && echo "$(date +%s),$r" >> "$LG/$tag.rss.csv"
      fi
      sleep 10
    done
  ) &
  local mpid=$!
  wait $tpid
  local rc=$?
  kill $mpid 2>/dev/null
  local e
  e=$(date +%s)
  local peak
  peak=$(awk -F, 'NR>1&&$2>m{m=$2} END{printf "%.2f", m/1048576}' "$LG/$tag.rss.csv" 2>/dev/null)
  if [ $rc -eq 0 ] && [ -s "$out/flow_summary.csv" ]; then
    echo "$rc $((e-s))" > "$out/DONE"; echo "OK  $tag $((e-s))s peakRSS=${peak}GB"
  else
    echo "FAIL $tag rc=$rc peakRSS=${peak}GB"; tail -3 "$LG/$tag.log"
  fi
}

lane() { for t in "$@"; do run_cell "$t"; done; }

# 0. archive round-2 results (mv, no deletion; manifest first)
if [ ! -d "$V2/results_r2_floor1ns" ] && [ -d "$RS/pf_single_10g" ]; then
  mkdir -p "$V2/results_r2_floor1ns"
  ls -laR "$RS" > "$V2/results_r2_floor1ns/MANIFEST_pre_move.txt"
  mv "$RS"/pf_single_* "$RS"/pf_burst_* "$RS"/heff_* "$V2/results_r2_floor1ns/" 2>/dev/null
  cp "$V2/reports/01_preflight_results.csv" "$V2/reports/02_heff_measurement.csv" \
     "$V2/results_r2_floor1ns/" 2>/dev/null
  echo "round-2 results archived to results_r2_floor1ns/"
fi

# 1. twin byte-regression, keyed to the CURRENT binary sha: all new flags
# (qlen_ts, TX_TIME_ROUND_NS, CBAP_TX_RECORDS_MAX) default OFF must be inert.
cursha=$(sha256sum "$BIN" | awk '{print $1}')
if [ -f "$LG/REGV3_OK" ] && grep -q "$cursha" "$LG/REGV3_OK"; then
  echo "regression already passed for binary $cursha, skipping"
else
  cd /work/simulation/experiment/scheme1_sba || exit 2
  rm -rf regv3_b040_out && mkdir -p regv3_b040_out
  sed 's#regv2_b040_out#regv3_b040_out#g' regv2_b040.txt > regv3_b040.txt
  timeout -k 60 7200 "$BIN" regv3_b040.txt > "$LG/regv3_b040.log" 2>&1 \
    || { echo REG_RUN_FAIL; tail -5 "$LG/regv3_b040.log"; exit 3; }
  bad=0
  for f in flow_summary.csv selected_link_timeseries.csv rate_transition.csv \
           round_summary.csv pfc_events.csv flow_timing.csv; do
    a=$(sha256sum scr8_b040_out/$f | cut -c1-16)
    b=$(sha256sum regv3_b040_out/$f | cut -c1-16)
    [ "$a" = "$b" ] && echo "  identical $f" || { echo "  DIFFERS $f"; bad=1; }
  done
  [ $bad -ne 0 ] && { echo "NEW_FLAGS_NOT_INERT -- STOP"; exit 4; }
  echo "$cursha  $BIN" > "$LG/REGV3_OK"
  echo "REGRESSION OK (all v2 flags inert at flag-off, binary $cursha)"
fi

# 2. nine cells, three rate lanes in parallel
cd "$CF" || exit 2
lane pf_single_10g  pf_burst_10g  heff_10g  > "$LG/lane10.log"  2>&1 &
lane pf_single_200g pf_burst_200g heff_200g > "$LG/lane200.log" 2>&1 &
lane pf_single_400g pf_burst_400g heff_400g > "$LG/lane400.log" 2>&1 &
wait
cat "$LG/lane10.log" "$LG/lane200.log" "$LG/lane400.log"
echo "=== round-3 preflight complete ==="
python3 /work/v2_400g/pf_analyze.py
