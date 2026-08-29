#!/bin/bash
export LD_LIBRARY_PATH=/work/simulation/build:${LD_LIBRARY_PATH:-}
LOG=/work/b3.log
cd /work/simulation/experiment/scheme1_sba || exit 1
sha256sum /work/simulation/build/scratch/third >> "$LOG"
mk () {
  local out="mb_$1_out" cfg="mb_$1.txt"
  sed "s|ct_cbap_off_out|${out}|g" ct_cbap_off.txt > "$cfg"
  { echo "CBAP_PHASE_SPREAD_ENABLE $2"
    echo "CBAP_STEADY_CAP_ENABLE $3"
    echo "CBAP_SBA_STEADY_FILL 0"
    echo "CBAP_HOLD_TRACK_TARGET 0"; } >> "$cfg"
  mkdir -p "$out"
}
mk off 0 0
mk phase 1 0
mk both 1 1
for a in off phase both; do
  o="mb_${a}_out"
  [ -f "$o/DONE" ] && continue
  free=$(df --output=avail -BG /work | tail -1 | tr -dc '0-9')
  [ "${free:-0}" -lt 1 ] && { echo "INVALID_LOW_DISK ${free}G" >> "$LOG"; exit 1; }
  echo "$o start $(date -u +%H:%M:%S) free=${free}G" >> "$LOG"
  /work/simulation/build/scratch/third "mb_$a.txt" > "/tmp/$o.txt" 2>&1
  echo "$o exit=$? $(date -u +%H:%M:%S)" >> "$LOG"
  [ -s "$o/flow_summary.csv" ] && touch "$o/DONE" || \
    { grep -m1 -E "CONFIG_ERROR|INVALID_|assert" "/tmp/$o.txt" >> "$LOG"; exit 1; }
done
echo "B3_ALL_DONE" >> "$LOG"
