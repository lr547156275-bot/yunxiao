#!/bin/bash
# Frontier-extension run: 21 ultra-low-threshold baseline cells from
# configs/FX_TAGS.txt, 2-worker pool, resume-safe, RSS-sampled.  Launch:
#   docker exec -d hpcc-build bash -c \
#     'setsid /work/run_v2fx.sh > /work/v2_400g/logs/fx_console.log 2>&1'
set -u
export LD_LIBRARY_PATH=/work/simulation/build:${LD_LIBRARY_PATH:-}
export BIN=/work/simulation/build/scratch/third
export V2=/work/v2_400g
export LG=$V2/logs
export RS=$V2/results

cursha=$(sha256sum "$BIN" | awk '{print $1}')
grep -q "$cursha" "$LG/REGV4_OK" 2>/dev/null \
  || { echo "REGRESSION MARKER MISMATCH -- binary changed, stop"; exit 5; }
[ -s "$V2/configs/FX_TAGS.txt" ] \
  || { echo "FX_TAGS.txt missing -- run: python3 /work/mk_v2.py frontier_ext"; exit 6; }

run_cell() {
  local tag=$1
  local out=$RS/$tag
  if [ -f "$out/DONE" ]; then echo "SKIP $tag (already done)"; return 0; fi
  local free
  free=$(df -BG /work | awk 'NR==2{gsub("G","",$4); print $4}')
  if [ "$free" -lt 1 ]; then echo "DISK_GUARD_FAIL $tag (cell not started)"; return 9; fi
  mkdir -p "$out"
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
xargs -P"${SCR_P:-2}" -I{} bash -c 'run_cell "$@"' _ {} \
  < "$V2/configs/FX_TAGS.txt"
echo "=== frontier extension complete ==="
python3 /work/fx_analyze.py
