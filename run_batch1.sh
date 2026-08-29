#!/bin/bash
# Batch 1: S1/S2/S3/S6 x {CBAP, DCQCN} = 8 cells, strictly serial (MAX_JOBS=1).
#
# Disk discipline (section E):
#   * pre-start:  available must be >= 2.0 GB, else refuse to start (exit 4)
#   * mid-run:    a watchdog aborts the cell if available drops below 1.5 GB,
#                 marking it INVALID_LOW_DISK with a non-zero exit -- never a
#                 silently truncated trace
#   * nothing valid is ever deleted
#
# Acceptance is run IMMEDIATELY after each cell (section D); a failure stops the
# batch (section F) and no later cell is started.
set -u
cd /work/simulation/experiment/scheme1_sba || exit 2

MAX_JOBS=1
[ "$MAX_JOBS" = "1" ] || { echo "MAX_JOBS must be 1"; exit 2; }

MIN_START_GB=2.0
MIN_ABORT_GB=1.5
LOG=/work/simulation/experiment/scheme1_sba/CHECKPOINT_PROVENANCE/BATCH1_LOG.txt
: > "$LOG"

# The container mounts the workspace at /work (same /dev/loop4 the host sees as
# /workspaces).  Fail closed: an unreadable df must never look like plenty of
# space, so an empty result is treated as 0.
avail_gb() {
  local v
  v=$(df -B1 /work 2>/dev/null | tail -1 | awk '{printf "%.2f", $4/1024/1024/1024}')
  [ -n "$v" ] || v=0
  echo "$v"
}

say() { echo "$*" | tee -a "$LOG"; }

ORDER="cbap_s1 dcqcn_s1 cbap_s2 dcqcn_s2 cbap_s3 dcqcn_s3 cbap_s6 dcqcn_s6"

for cell in $ORDER; do
  cfg="ckpt3_${cell}.txt"
  out="ckpt3_${cell}_out"
  [ -f "$cfg" ] || { say "MISSING CONFIG $cfg"; exit 2; }

  A=$(avail_gb)
  say ""
  say "================================================================"
  say "CELL $cell   disk_available_before=${A} GB   (min ${MIN_START_GB} GB)"
  say "================================================================"
  if awk -v a="$A" -v m="$MIN_START_GB" 'BEGIN{exit !(a < m)}'; then
    say "REFUSING TO START: available ${A} GB < ${MIN_START_GB} GB"
    echo "STATUS=INVALID_LOW_DISK" > "$out/INVALID_LOW_DISK.txt" 2>/dev/null
    echo "available_gb=$A" >> "$out/INVALID_LOW_DISK.txt" 2>/dev/null
    exit 4
  fi

  # mid-run watchdog
  ( while true; do
      sleep 20
      B=$(avail_gb)
      if awk -v a="$B" -v m="$MIN_ABORT_GB" 'BEGIN{exit !(a < m)}'; then
        pkill -f "third $cfg" 2>/dev/null
        echo "STATUS=INVALID_LOW_DISK" > "$out/INVALID_LOW_DISK.txt"
        echo "aborted_at_available_gb=$B" >> "$out/INVALID_LOW_DISK.txt"
        echo "reason=mid-run disk below ${MIN_ABORT_GB} GB; trace would be truncated" >> "$out/INVALID_LOW_DISK.txt"
        exit 0
      fi
      pgrep -f "third $cfg" >/dev/null || exit 0
    done ) &
  WD=$!

  T0=$(date +%s)
  LD_LIBRARY_PATH=/work/simulation/build /work/simulation/build/scratch/third "$cfg" > "$out/run.log" 2>&1
  RC=$?
  T1=$(date +%s)
  kill $WD 2>/dev/null; wait $WD 2>/dev/null

  say "exit_code=$RC  wall=$((T1-T0))s  disk_after=$(avail_gb) GB  out_size=$(du -sh "$out" | cut -f1)"

  if [ -f "$out/INVALID_LOW_DISK.txt" ]; then
    say "CELL $cell ABORTED: INVALID_LOW_DISK"
    exit 5
  fi
  if [ "$RC" -ne 0 ]; then
    say "CELL $cell FAILED with exit $RC -- stopping batch, retaining everything"
    tail -5 "$out/run.log" | tee -a "$LOG"
    exit 6
  fi

  ERR=$(grep -c -E 'CONFIG_ERROR|INVALID_RECORDER_ATTACH|Drop:|LOG_TRUNCATED' "$out/run.log" 2>/dev/null || echo 0)
  say "error_lines=$ERR"
  if [ "$ERR" -ne 0 ]; then
    say "CELL $cell has error lines -- stopping batch"
    grep -E 'CONFIG_ERROR|INVALID_RECORDER_ATTACH|Drop:|LOG_TRUNCATED' "$out/run.log" | head -5 | tee -a "$LOG"
    exit 7
  fi

  ATT=$(grep -c TX_RECORDER_ATTACHED "$out/run.log" 2>/dev/null || echo 0)
  EXPN=$(awk 'NR>1' "s${cell##*_s}_cbap_link.txt" 2>/dev/null | wc -l)
  say "recorder_attached=$ATT expected_links=$EXPN"
  say "tx_trace_lines=$(wc -l < "$out/tx_serialization.csv" 2>/dev/null || echo 0)"
  say "CELL $cell COMPLETE"
done

say ""
say "BATCH 1 COMPLETE: 8/8 cells ran"
