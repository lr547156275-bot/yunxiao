#!/bin/bash
# v2 FORMAL MATRIX: determinism twin first, then all cells from
# configs/MATRIX_TAGS.txt through a 2-worker pool.  Resume-safe (DONE
# markers), RSS-sampled, disk-guarded.  Launch detached:
#   docker exec -d hpcc-build bash -c \
#     'setsid /work/run_v2matrix.sh > /work/v2_400g/logs/matrix_console.log 2>&1'
set -u
export LD_LIBRARY_PATH=/work/simulation/build:${LD_LIBRARY_PATH:-}
export BIN=/work/simulation/build/scratch/third
export V2=/work/v2_400g
export LG=$V2/logs
export RS=$V2/results

cursha=$(sha256sum "$BIN" | awk '{print $1}')
grep -q "$cursha" "$LG/REGV4_OK" 2>/dev/null \
  || { echo "REGRESSION MARKER MISMATCH -- rerun the regression first"; exit 5; }
[ -s "$V2/configs/MATRIX_TAGS.txt" ] \
  || { echo "MATRIX_TAGS.txt missing -- run: python3 /work/mk_v2.py matrix"; exit 6; }

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

# 0. single-seed determinism twin at 400G (once per binary)
cd "$V2/configs" || exit 2
if [ ! -f "$LG/DET_TWIN_OK" ]; then
  echo "determinism twin: fm400g_s2_cbap twice, byte-compare"
  mkdir -p "$RS/det_twin"
  sed "s#$RS/fm400g_s2_cbap#$RS/det_twin#g" fm400g_s2_cbap.txt > det_twin.txt
  timeout -k 60 7200 "$BIN" fm400g_s2_cbap.txt > "$LG/det_a.log" 2>&1 \
    || { echo DET_RUN_A_FAIL; exit 7; }
  timeout -k 60 7200 "$BIN" det_twin.txt > "$LG/det_b.log" 2>&1 \
    || { echo DET_RUN_B_FAIL; exit 7; }
  bad=0
  for fcsv in flow_summary.csv flow_timing.csv rate_transition.csv \
              pfc_events.csv round_summary.csv; do
    a=$(sha256sum "$RS/fm400g_s2_cbap/$fcsv" | cut -c1-16)
    b=$(sha256sum "$RS/det_twin/$fcsv" | cut -c1-16)
    [ "$a" = "$b" ] && echo "  identical $fcsv" \
      || { echo "  DIFFERS $fcsv"; bad=1; }
  done
  [ $bad -ne 0 ] && { echo "DETERMINISM_BROKEN -- STOP"; exit 8; }
  echo "0 twin" > "$RS/fm400g_s2_cbap/DONE"
  sha256sum "$BIN" > "$LG/DET_TWIN_OK"
  echo "DETERMINISM OK (single seed justified at 400G)"
fi

# 1. the matrix
xargs -P"${SCR_P:-2}" -I{} bash -c 'run_cell "$@"' _ {} \
  < "$V2/configs/MATRIX_TAGS.txt"
echo "=== formal matrix complete ==="
python3 /work/matrix_analyze.py
