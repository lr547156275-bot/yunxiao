#!/bin/bash
# v2 OVERNIGHT run (approved plan: comprehensive screening exploration).
# Fully resume-safe: rerunning this script skips every completed step.
#   1. archive bg-freeze-era results (mv, never delete)
#   2. twin byte-regression for the payload64 fix (binary-sha-keyed marker)
#   3. re-measure heff_400g with live background -> derive H_GUARD
#   4. regenerate screening configs (9 base + 11 extension + 2 epoch)
#   5. run all 22 cells, 2-worker pool, RSS-sampled
#   6. rerun pf_burst_400g (its round-3 bg was frozen too)
#   7. analyzers (screening winner by frozen rules; preflight refresh)
set -u
export LD_LIBRARY_PATH=/work/simulation/build:${LD_LIBRARY_PATH:-}
export BIN=/work/simulation/build/scratch/third
export V2=/work/v2_400g
export LG=$V2/logs
export RS=$V2/results

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

# 1. archive the bg-freeze-era results (screening round 1, heff_400g r3,
#    pf_burst_400g r3) -- mv, never delete
ARCH=$V2/results_bgfreeze_era
if [ ! -d "$ARCH" ]; then
  mkdir -p "$ARCH"
  ls -laR "$RS" > "$ARCH/MANIFEST_pre_move.txt"
  mv "$RS"/scrv2_* "$RS/heff_400g" "$RS/pf_burst_400g" "$ARCH/" 2>/dev/null
  cp "$V2/reports/04_screening_results.csv" "$ARCH/" 2>/dev/null
  echo "bg-freeze-era results archived to $ARCH/"
fi

# 2. twin byte-regression for the payload64 fix
cursha=$(sha256sum "$BIN" | awk '{print $1}')
if [ -f "$LG/REGV4_OK" ] && grep -q "$cursha" "$LG/REGV4_OK"; then
  echo "regression already passed for binary $cursha, skipping"
else
  cd /work/simulation/experiment/scheme1_sba || exit 2
  rm -rf regv4_b040_out && mkdir -p regv4_b040_out
  sed 's#regv2_b040_out#regv4_b040_out#g' regv2_b040.txt > regv4_b040.txt
  timeout -k 60 7200 "$BIN" regv4_b040.txt > "$LG/regv4_b040.log" 2>&1 \
    || { echo REG_RUN_FAIL; tail -5 "$LG/regv4_b040.log"; exit 3; }
  bad=0
  for f in flow_summary.csv selected_link_timeseries.csv rate_transition.csv \
           round_summary.csv pfc_events.csv flow_timing.csv; do
    a=$(sha256sum scr8_b040_out/$f | cut -c1-16)
    b=$(sha256sum regv4_b040_out/$f | cut -c1-16)
    [ "$a" = "$b" ] && echo "  identical $f" || { echo "  DIFFERS $f"; bad=1; }
  done
  [ $bad -ne 0 ] && { echo "PAYLOAD64_NOT_INERT -- STOP"; exit 4; }
  echo "$cursha  $BIN" > "$LG/REGV4_OK"
  echo "REGRESSION OK (payload64 fix inert at <2^32, binary $cursha)"
fi

# 3. re-measure heff_400g with a live background flow
cd "$V2/configs" || exit 2
run_cell heff_400g
[ -f "$RS/heff_400g/DONE" ] || { echo "HEFF_RERUN_FAILED -- STOP"; exit 6; }
python3 /work/heff_hg.py || { echo "HG_EXTRACT_FAILED -- STOP"; exit 7; }

# 4. regenerate screening configs with the measured H_GUARD.  Stale configs
# from the 9-cell round-1 grid are moved aside first so the tag glob below
# only sees the 8-cell cross.
mkdir -p "$V2/configs_prev_scr1"
mv "$V2/configs"/scrv2_* "$V2/configs_prev_scr1/" 2>/dev/null
python3 /work/mk_v2.py screening

# 5. all 8 cross cells, 2-worker pool
cd "$V2/configs" || exit 2
TAGS=$(ls scrv2_*.txt | sed 's/\.txt$//')
printf '%s\n' $TAGS | xargs -P"${SCR_P:-2}" -I{} bash -c 'run_cell "$@"' _ {}

# 6. pf_burst_400g rerun (bg frozen in round 3)
run_cell pf_burst_400g

# 7. analyzers
echo "=== overnight complete ==="
python3 /work/scr_analyze.py
python3 /work/v2_400g/pf_analyze.py 2>/dev/null | tail -12
