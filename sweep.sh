#!/bin/bash
# CBAP Pareto sweep, phase 1.  Serial-safe, 2-way parallel (2 cores measured).
#
# Frozen and untouched: S3 topology, s3_flow.txt, s3_cbap_{link,path}.txt,
# s3_round_schedule.txt, seed 2, pg=3, MIN_RATE, Q_low/Q_high/Q_red/Q_abs,
# ECN/PFC thresholds, every checker.  Reference cell mb_both_out is NOT touched.
#
# Grid (9 cells):
#   CBAP  cap in {0.995, 1.000} x rho in {0.75, 0.90, 0.9875}      = 6
#   CBAP  cap=0.995 rho=0.90 MAX_BOOST=0.40  (empirical inertness) = 1
#   DCQCN (CC_MODE 1), HPCC (CC_MODE 3, params from au_s3_hpcc.txt) = 2
set -u
JOBS=${JOBS:-2}
BASE=/work/simulation/experiment/scheme1_sba
LOG=/work/sweep.log
export LD_LIBRARY_PATH=/work/simulation/build:${LD_LIBRARY_PATH:-}
BIN=/work/simulation/build/scratch/third
cd "$BASE" || exit 1

{
  echo "SWEEP_START $(date -u +%Y-%m-%dT%H:%M:%SZ)  JOBS=$JOBS"
  sha256sum "$BIN" /work/simulation/build/libns3.18-point-to-point-debug.so
  sha256sum s3_flow.txt s3_cbap_link.txt s3_cbap_path.txt s3_round_schedule.txt \
            topology.txt
  df -h /work | tail -1
} >> "$LOG"

mkcbap () {   # $1 tag  $2 cap  $3 rho  $4 boost
  local out="pa_$1_out" cfg="pa_$1.txt"
  sed -e "s|ct_cbap_off_out|${out}|g" \
      -e "s|^CBAP_RHO .*|CBAP_RHO $3|" \
      -e "s|^CBAP_QC_MAX_BOOST_RATIO .*|CBAP_QC_MAX_BOOST_RATIO $4|" \
      ct_cbap_off.txt > "$cfg"
  { echo "CBAP_PHASE_SPREAD_ENABLE 1"
    echo "CBAP_STEADY_CAP_ENABLE 1"
    echo "CBAP_STEADY_CAP_FRACTION $2"
    echo "CBAP_SBA_STEADY_FILL 0"
    echo "CBAP_HOLD_TRACK_TARGET 0"; } >> "$cfg"
  mkdir -p "$out"
  echo "$1"
}

mkbase () {   # $1 tag  $2 cc_mode
  local out="pa_$1_out" cfg="pa_$1.txt"
  sed -e "s|ct_cbap_off_out|${out}|g" \
      -e "s|^CC_MODE .*|CC_MODE $2|" \
      -e "s|^CBAP_ENABLE .*|CBAP_ENABLE 0|" \
      ct_cbap_off.txt > "$cfg"
  mkdir -p "$out"
  echo "$1"
}

CELLS=""
for cap in 0.995 1.000; do
  for rho in 0.75 0.90 0.9875; do
    t="cap${cap/./}_rho${rho/./}"
    mkcbap "$t" "$cap" "$rho" 0.30 >/dev/null
    CELLS="$CELLS $t"
  done
done
mkcbap "cap0995_rho090_b040" 0.995 0.90 0.40 >/dev/null
CELLS="$CELLS cap0995_rho090_b040"
mkbase dcqcn 1 >/dev/null; CELLS="$CELLS dcqcn"
mkbase hpcc  3 >/dev/null; CELLS="$CELLS hpcc"

echo "cells:$CELLS" >> "$LOG"

run_one () {
  local t="$1" out="pa_$1_out"
  [ -f "$out/DONE" ] && { echo "$t SKIP(done)" >> "$LOG"; return 0; }
  local free
  free=$(df --output=avail -BG /work | tail -1 | tr -dc '0-9')
  if [ "${free:-0}" -lt 2 ]; then
    echo "$t INVALID_LOW_DISK ${free}G" >> "$LOG"; return 1
  fi
  echo "$t START $(date -u +%H:%M:%S) free=${free}G" >> "$LOG"
  "$BIN" "pa_$1.txt" > "/tmp/pa_$1.txt" 2>&1
  local rc=$?
  echo "$t EXIT=$rc $(date -u +%H:%M:%S)" >> "$LOG"
  if [ "$rc" -eq 0 ] && [ -s "$out/flow_summary.csv" ]; then
    touch "$out/DONE"; echo "$t DONE" >> "$LOG"
  else
    grep -m1 -E "CONFIG_ERROR|INVALID_|assert" "/tmp/pa_$1.txt" >> "$LOG"
  fi
}

n=0
for t in $CELLS; do
  run_one "$t" &
  n=$((n+1))
  if [ "$n" -ge "$JOBS" ]; then wait; n=0; fi
done
wait

{ echo "SWEEP_ALL_DONE $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  df -h /work | tail -1
  ls -d pa_*_out/DONE 2>/dev/null | wc -l; } >> "$LOG"
