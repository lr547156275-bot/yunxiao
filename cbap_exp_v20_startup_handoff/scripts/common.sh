#!/usr/bin/env bash
set -uo pipefail
V20_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$V20_ROOT/.." && pwd)"
SIM_ROOT="$REPO_ROOT/simulation"
MAX_JOBS="${MAX_JOBS:-4}"
MIN_FREE_GB="${MIN_FREE_GB:-5}"
RUN_TIMEOUT_MIN="${RUN_TIMEOUT_MIN:-60}"
KEEP_RAW="${KEEP_RAW:-0}"
export NS_LOG=""
ulimit -c 0

disk_check() {
  mkdir -p "$1"
  local free_kb need_kb
  free_kb="$(df -Pk "$1" | awk 'NR==2{print $4}')"
  need_kb="$(awk -v x="$MIN_FREE_GB" 'BEGIN{printf "%.0f",x*1024*1024}')"
  (( free_kb >= need_kb )) || {
    echo "REFUSE: less than ${MIN_FREE_GB} GiB free" >&2
    return 1
  }
}

finalize_meta() {
  python3 - "$1" "$2" "$3" <<'PY'
import json, os, sys, time
directory, status, elapsed = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
path = os.path.join(directory, "run_meta.json")
meta = json.load(open(path))
log = open(os.path.join(directory, "run.log"), errors="replace").read()
meta.update(exit_status=status, runtime_seconds=elapsed,
            end_time_unix=time.time(),
            status="finished" if status == 0 else "failed",
            ns3_executed=True, log_truncated=("TRUNCATED" in log))
temporary = path + ".tmp"
open(temporary, "w").write(json.dumps(meta, indent=2, sort_keys=True)+"\n")
os.replace(temporary, path)
PY
}

postprocess_one() {
  local directory="$1" expected="$2"
  python3 "$REPO_ROOT/cbap_exp/scripts/collect_run_metrics.py" \
    "$directory" || return 1
  python3 "$REPO_ROOT/cbap_exp/scripts/materialize_required_summaries.py" \
    "$directory" || return 1
  python3 "$REPO_ROOT/cbap_final_metric_pipeline/scripts/collect_full_work_metrics.py" \
    --run-dir "$directory" --output-dir "$directory" || return 1
  python3 "$V20_ROOT/scripts/check_outputs.py" --allow-no-complete-flag \
    --expected "$expected" "$directory" || return 1
  touch "$directory/completed.flag"
  if [[ "$KEEP_RAW" != 1 ]]; then
    local file
    for file in selected_link_timeseries.csv selected_flow_timeseries.csv \
        sender_tx_trace.csv; do
      [[ ! -f "$directory/$file" ]] || gzip -f "$directory/$file"
    done
  fi
}

archive_invalid_attempt() {
  local directory="$1" archive
  archive="$directory/failed_attempts/attempt_$(date +%Y%m%d_%H%M%S)"
  mkdir -p "$archive"
  find "$directory" -mindepth 1 -maxdepth 1 ! -name failed_attempts \
    -exec mv -t "$archive" -- {} +
}

full_work_is_incomplete() {
  python3 - "$1/result_full_work.json" <<'PY'
import json, os, sys
path = sys.argv[1]
if not os.path.isfile(path):
    raise SystemExit(1)
raise SystemExit(0 if not json.load(open(path)).get("all_flows_completed")
                 else 1)
PY
}

run_one() {
  local manifest="$1" output_root="$2" run_id="$3"
  local scenario algorithm seed expected directory start status elapsed
  read -r scenario algorithm seed expected < <(python3 - "$manifest" "$run_id" <<'PY'
import csv, sys
for row in csv.DictReader(open(sys.argv[1])):
    if row["run_id"] == sys.argv[2]:
        print(row["scenario"], row["algorithm_name"], row["seed"],
              row.get("expected", "MEASURE"))
        break
else:
    raise SystemExit("unknown run")
PY
)
  directory="$output_root/$scenario/$algorithm/seed_$seed"
  if [[ -f "$directory/completed.flag" ]] && \
      python3 "$V20_ROOT/scripts/check_outputs.py" \
      --expected "$expected" "$directory" \
      >/dev/null 2>&1; then
    echo "SKIP valid $run_id"
    return 0
  fi
  if [[ -f "$directory/exit_status.txt" ]] &&
      [[ "$(tr -d '[:space:]' < "$directory/exit_status.txt")" == 0 ]] &&
      [[ -s "$directory/flow_summary.csv" ]] &&
      [[ -s "$directory/round_summary.csv" ]] &&
      [[ -s "$directory/cbap_v20_batch.csv" ]] &&
      [[ -s "$directory/cbap_v20_flow.csv" ]]; then
    if postprocess_one "$directory" "$expected"; then
      echo "RECOVERED postprocessing $run_id"
      return 0
    fi
    if full_work_is_incomplete "$directory" || [[ "$expected" != MEASURE ]]; then
      echo "RERUN invalid result $run_id" >&2
      archive_invalid_attempt "$directory"
    else
      echo "FAIL postprocessing recovery $run_id (simulation not rerun)" >&2
      return 1
    fi
  fi
  if [[ -d "$directory" ]] &&
      [[ -n "$(find "$directory" -mindepth 1 -maxdepth 1 \
          ! -name failed_attempts -print -quit 2>/dev/null)" ]]; then
    archive_invalid_attempt "$directory"
  fi
  disk_check "$output_root" || return 1
  mkdir -p "$directory"
  python3 "$V20_ROOT/scripts/prepare_run.py" "$manifest" "$run_id" \
    "$directory" --min-free-gb "$MIN_FREE_GB" || return 1
  rm -f "$directory/completed.flag" "$directory/exit_status.txt"
  start="$(date +%s)"
  set +e
  (cd "$SIM_ROOT" && timeout --signal=TERM --kill-after=30s \
    "${RUN_TIMEOUT_MIN}m" python2 ./waf --cwd="$directory" \
    --run "scratch/third $directory/config.txt") \
    > "$directory/run.full.log" 2>&1
  status=$?
  set -e
  tail -c 10485760 "$directory/run.full.log" > "$directory/run.log"
  [[ "$KEEP_RAW" == 1 ]] || rm -f "$directory/run.full.log"
  elapsed="$(( $(date +%s) - start ))"
  echo "$status" > "$directory/exit_status.txt"
  finalize_meta "$directory" "$status" "$elapsed"
  if (( status != 0 )); then
    echo "FAIL $run_id exit=$status (diagnostics retained)" >&2
    return "$status"
  fi
  postprocess_one "$directory" "$expected" || return 1
  echo "PASS $run_id"
}

run_manifest() {
  local manifest="$1" output_root="$2" failed=0 run_id
  trap 'jobs -pr | xargs -r kill; wait; exit 130' INT TERM
  while IFS= read -r run_id; do
    while (( $(jobs -pr | wc -l) >= MAX_JOBS )); do
      wait -n || failed=1
    done
    run_one "$manifest" "$output_root" "$run_id" &
  done < <(python3 - "$manifest" <<'PY'
import csv, sys
for row in csv.DictReader(open(sys.argv[1])):
    print(row["run_id"])
PY
)
  while (( $(jobs -pr | wc -l) )); do
    wait -n || failed=1
  done
  return "$failed"
}
