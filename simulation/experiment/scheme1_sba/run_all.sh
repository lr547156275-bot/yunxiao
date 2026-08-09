#!/bin/bash
# Final paper matrix driver: 5 algorithms x 6 scenarios = 30 cells, one seed.
#
# Usage (inside the container):
#   setsid nohup bash /work/simulation/experiment/scheme1_sba/run_all.sh \
#       >> /work/matrix_logs/run_all.out 2>&1 &
#
# Safe to re-run at any time.  run_matrix.sh skips cells that already carry a
# .done flag, so a container restart costs at most the cell that was in flight.
# Nothing is ever deleted.
#
# Order is deliberate: the cheap scenarios and the dual-bottleneck case come
# first, so a late platform failure costs the least-informative results.  S4 and
# S5 dominate the runtime (~15h of ~20h) and run last.
set -u

SIM=/work/simulation
D=experiment/scheme1_sba
LOGS=/work/matrix_logs
SEED=${SEED:-2}
cd "$SIM"
mkdir -p "$LOGS"

# Single instance.  A killed run leaves a stale lock; clear it rather than
# blocking every future resume.
LOCK=$LOGS/run_all.lock
if [ -f "$LOCK" ]; then
  oldpid=$(cat "$LOCK" 2>/dev/null || echo "")
  if [ -n "$oldpid" ] && kill -0 "$oldpid" 2>/dev/null; then
    echo "$(date +%H:%M:%S) already running as pid $oldpid; exiting"
    exit 0
  fi
  echo "$(date +%H:%M:%S) stale lock from pid ${oldpid:-?} cleared"
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

# scenario:stop_time:cell_timeout_seconds
# Stop times are the already-validated values; timeouts are ~4x the measured
# per-cell wall time so a hung cell fails as an anomaly rather than stalling.
PLAN="s1:2.1:3600 s2:2.5:5400 s3:3.0:10800 s6:2.5:5400 s4:5.5:28800 s5:6.0:28800"

echo "=============================================================="
echo " FINAL MATRIX  seed=$SEED  order: s1 s2 s3 s6 s4 s5"
echo " started $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=============================================================="

for entry in $PLAN; do
  tag=${entry%%:*}
  rest=${entry#*:}
  stop=${rest%%:*}
  tmo=${rest##*:}
  # Count only this seed.  A bare m_*_<tag>_*.done glob also matches flags from
  # earlier multi-seed runs, which made the driver skip a scenario it had not
  # actually produced for this matrix.
  ndone=$(ls "$LOGS"/m_*_${tag}_seed${SEED}.done 2>/dev/null | wc -l)
  if [ "$ndone" -ge 5 ]; then
    echo ""
    echo ">>> $tag already complete (5/5), skipping"
    continue
  fi
  echo ""
  echo ">>> $tag  stop=${stop}s  timeout=${tmo}s  ($ndone/5 already done)"
  MAX_JOBS=1 CELL_TIMEOUT=$tmo bash $D/run_matrix.sh "$tag" "$stop" "$SEED"
  rc=$?
  if [ $rc -ne 0 ]; then
    echo ""
    echo "!!! $tag FAILED (rc=$rc).  Stopping the matrix so the anomaly can be"
    echo "    inspected rather than buried under later scenarios."
    echo "    Fix, then re-run this script -- completed cells are skipped."
    exit $rc
  fi
  # Extract as soon as the scenario finishes: a metric bug caught after s1
  # costs 11 minutes, caught after s5 it costs the whole run.
  echo ">>> extracting $tag"
  python2 $D/metrics.py "$tag" "$SEED" > "$LOGS/report_${tag}.txt" 2>&1 \
    && echo "    metrics ok -> $LOGS/report_${tag}.txt" \
    || echo "    METRICS FAILED for $tag (see $LOGS/report_${tag}.txt)"
  # Non-zero here means a controller had its required input and still did
  # nothing -- a real anomaly.  A scenario that is designed to keep an ECN
  # controller idle reports EXPECTED_NOT_ENGAGED and exits 0.
  if python2 $D/verify_triggers.py "$tag" "$SEED" "$LOGS/trig_${tag}.csv" \
        > "$LOGS/trig_${tag}.txt" 2>&1; then
    echo "    triggers ok -> $LOGS/trig_${tag}.txt"
  else
    echo "    !!! TRIGGER FAILURE in $tag -- a required mechanism did not engage"
    grep -E "^FAIL:" "$LOGS/trig_${tag}.txt" | sed 's/^/    /'
    echo "    stopping the matrix; inspect $LOGS/trig_${tag}.txt"
    exit 1
  fi
done

TOTAL=$(ls "$LOGS"/m_*_s?_seed${SEED}.done 2>/dev/null | wc -l)
echo ""
echo "=============================================================="
echo " MATRIX COMPLETE: $TOTAL/30 cells"
echo " finished $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=============================================================="
