#!/bin/bash
# v2 400G screening: 9 CBAP cells through a 4-worker pool (any free worker
# takes the next cell), per-cell RSS sampling, then the frozen-rule analyzer.
# Binary must be the round-3 one (regression marker checked, not re-run).
set -u
export LD_LIBRARY_PATH=/work/simulation/build:${LD_LIBRARY_PATH:-}
export BIN=/work/simulation/build/scratch/third
export V2=/work/v2_400g
export LG=$V2/logs
export RS=$V2/results

cursha=$(sha256sum "$BIN" | awk '{print $1}')
grep -q "$cursha" "$LG/REGV3_OK" 2>/dev/null \
  || { echo "REGRESSION MARKER MISMATCH -- rerun run_v2pf3.sh first"; exit 5; }

run_cell() {
  local tag=$1
  local out=$RS/$tag
  local free
  free=$(df -BG /work | awk 'NR==2{gsub("G","",$4); print $4}')
  if [ "$free" -lt 1 ]; then echo "DISK_GUARD_FAIL $tag (cell not started)"; return 9; fi
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
export -f run_cell

cd "$V2/configs" || exit 2
TAGS=""
for dt in 08 16 32; do
  for bm in 020 040 060; do
    TAGS="$TAGS scrv2_d${dt}_b${bm}"
  done
done
printf '%s\n' $TAGS | xargs -P4 -I{} bash -c 'run_cell "$@"' _ {}
echo "=== screening complete ==="
python3 /work/scr_analyze.py
