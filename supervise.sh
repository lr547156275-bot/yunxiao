#!/bin/bash
# Self-healing supervisor for the batch-1 runner.
#
# The Codespace VM has restarted three times (~06:07, ~07:51, ~09:07), each time
# killing the in-flight cell (container exits 128, OOMKilled=false, memory fine).
# The 10-minute cron poll never fired because cron only runs while the REPL is
# idle.  This loop lives INSIDE the container and depends on neither.
#
# EXECUTION LAYER ONLY: it re-launches run_batch1_v3.sh, which skips already
# accepted cells via their .binary marker.  No parameter, threshold, config,
# checker or result is modified.  It exits on completion or on a real acceptance
# failure -- it does NOT retry a genuine STOP.
set -u
cd /work/simulation/experiment/scheme1_sba || exit 2
LOG=CHECKPOINT_PROVENANCE/SUPERVISOR_LOG.txt
say() { echo "[$(date -u '+%H:%M:%S')] $*" >> "$LOG"; }
say "supervisor started pid=$$"

for i in $(seq 1 400); do            # ~6.7 h ceiling at 60 s
  OK=$(grep -cE 'CELL .* ACCEPTED' CHECKPOINT_PROVENANCE/BATCH1_V3_LOG.txt 2>/dev/null || echo 0)
  if [ "$OK" -ge 8 ]; then say "8/8 accepted -- supervisor exiting"; exit 0; fi
  if grep -q '^STOP:' CHECKPOINT_PROVENANCE/BATCH1_V3_LOG.txt 2>/dev/null; then
    say "real STOP detected -- NOT retrying, supervisor exiting"; exit 1
  fi
  if ! pgrep -f run_batch1_v3 >/dev/null 2>&1; then
    say "runner absent (accepted=$OK/8) -- relaunching"
    nohup bash /work/run_batch1_v3.sh >> /tmp/b1v3.txt 2>&1 &
    sleep 15
    say "relaunched, runner pid=$(pgrep -f run_batch1_v3 | head -1)"
  fi
  sleep 60
done
say "supervisor loop ceiling reached"
