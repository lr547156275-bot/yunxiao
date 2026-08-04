#!/usr/bin/env bash
set -uo pipefail

MAIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SIM_ROOT="$(cd "$MAIN_ROOT/../.." && pwd)"
RUN_ROOT="${RUN_ROOT:-$MAIN_ROOT/runs}"
JOBS="${JOBS:-1}"
SEEDS="${SEEDS:-1}"
MIN_FREE_GB="${MIN_FREE_GB:-5}"
KEEP_RAW="${KEEP_RAW:-0}"
RUN_TIMEOUT_MIN="${RUN_TIMEOUT_MIN:-60}"
FORCE_RERUN="${FORCE_RERUN:-0}"
export NS_LOG=""
ulimit -c 0

main_disk_check() {
  mkdir -p "$RUN_ROOT"
  local free_kb required_kb
  free_kb="$(df -Pk "$RUN_ROOT" | awk 'NR==2 {print $4}')"
  required_kb="$(awk -v value="$MIN_FREE_GB" 'BEGIN {printf "%.0f", value*1024*1024}')"
  (( free_kb >= required_kb )) || {
    echo "REFUSE less than ${MIN_FREE_GB} GiB free at $RUN_ROOT" >&2
    return 1
  }
}

main_update_meta() {
  local run_dir="$1" status="$2" elapsed="$3"
  python3 - "$run_dir/run_meta.json" "$status" "$elapsed" <<'PY'
import json, os, sys, time
path, status, elapsed = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
data=json.load(open(path))
data.update({"exit_status":status, "runtime_seconds":elapsed,
             "end_time_unix":time.time(),
             "status":"finished" if status == 0 else "failed"})
tmp=path+".tmp"
with open(tmp,"w") as h:
    json.dump(data,h,indent=2,sort_keys=True); h.write("\n")
os.replace(tmp,path)
PY
}

main_mark_started() {
  local run_dir="$1"
  python3 - "$run_dir/run_meta.json" <<'PY'
import json, os, sys, time
path=sys.argv[1]; data=json.load(open(path))
data.update({"start_time_unix":time.time(), "status":"running"})
tmp=path+".tmp"
with open(tmp,"w") as h:
    json.dump(data,h,indent=2,sort_keys=True); h.write("\n")
os.replace(tmp,path)
PY
}

main_clear_outputs() {
  local run_dir="$1" name
  for name in completed.flag exit_status.txt runtime_seconds.txt stdout.log \
      flow_summary.csv round_summary.csv feedback_summary.csv \
      controller_summary.csv group_round_summary.csv flow_plan.csv \
      selected_link_timeseries.csv selected_link_timeseries.csv.gz \
      selected_flow_timeseries.csv selected_flow_timeseries.csv.gz \
      raw_wire_size_summary.csv raw_wire_size_summary.csv.gz \
      release_queue_summary.csv release_queue_summary.csv.gz \
      pfc_events.csv queue_summary.csv congestion_summary.csv \
      wire_summary.csv algorithm_summary.csv bop_qb_group_decisions.csv \
      bop_group_decisions.csv bop_flow_rates.csv; do
    rm -f "$run_dir/$name"
  done
}

main_run_one() {
  local scenario="$1" algorithm="$2" seed="$3"
  local run_dir="$RUN_ROOT/$scenario/$algorithm/seed_$seed"
  local start end elapsed status
  if [[ -f "$run_dir/completed.flag" ]]; then
    if python3 "$MAIN_ROOT/scripts/check_main_outputs.py" reuse "$run_dir" \
        >/dev/null 2>&1; then
      echo "SKIP valid $scenario $algorithm seed=$seed"
      return 0
    fi
    if [[ "$FORCE_RERUN" != "1" ]]; then
      echo "REFUSE completed run is invalid/hash-mismatched; set FORCE_RERUN=1: $run_dir" >&2
      return 2
    fi
  fi
  main_disk_check || return
  mkdir -p "$run_dir"
  main_clear_outputs "$run_dir"
  python3 "$MAIN_ROOT/scripts/prepare_main_run.py" \
    "$scenario" "$algorithm" "$seed" "$run_dir" \
    --min-free-gb "$MIN_FREE_GB" || return
  main_mark_started "$run_dir"
  start="$(date +%s)"
  set +e
  (
    cd "$SIM_ROOT" || exit 125
    timeout --signal=TERM --kill-after=30s "${RUN_TIMEOUT_MIN}m" \
      python2 ./waf --cwd="$run_dir" \
        --run "scratch/third $run_dir/config.txt"
  ) 2>&1 | tail -c 10485760 >"$run_dir/stdout.log"
  status="${PIPESTATUS[0]}"
  set -e
  end="$(date +%s)"
  elapsed="$((end-start))"
  printf '%s\n' "$status" >"$run_dir/exit_status.txt"
  printf '%s\n' "$elapsed" >"$run_dir/runtime_seconds.txt"
  main_update_meta "$run_dir" "$status" "$elapsed"
  if (( status != 0 )); then
    echo "FAIL $scenario $algorithm seed=$seed exit=$status (raw retained)" >&2
    return "$status"
  fi
  python3 "$MAIN_ROOT/scripts/collect_run_metrics.py" "$run_dir" || {
    echo "FAIL metric collection $run_dir (raw retained)" >&2
    return 1
  }
  python3 "$MAIN_ROOT/scripts/check_main_outputs.py" run \
    --pre-complete "$run_dir" || {
    echo "FAIL output validation $run_dir (raw retained)" >&2
    return 1
  }
  touch "$run_dir/completed.flag"
  if [[ "$KEEP_RAW" != "1" ]]; then
    local name
    for name in selected_flow_timeseries.csv selected_link_timeseries.csv \
                flow_plan.csv raw_wire_size_summary.csv \
                release_queue_summary.csv; do
      [[ ! -f "$run_dir/$name" ]] || gzip -f "$run_dir/$name"
    done
  fi
  echo "PASS $scenario $algorithm seed=$seed"
}

main_wait_slot() {
  while (( $(jobs -pr | wc -l) >= JOBS )); do
    wait -n || return 1
  done
}

main_run_rows() {
  local section_filter="$1" seeds_filter="$2"
  local failed=0 scenario algorithm seed section
  # SIGINT/SIGTERM stop new launches and terminate current simulator children.
  trap 'jobs -pr | xargs -r kill; wait; exit 130' INT TERM
  while IFS=, read -r run_id section scenario algorithm seed; do
    # Python's csv module commonly emits CRLF. The final field otherwise
    # becomes "1\r" and silently fails the SEEDS=1 membership test.
    seed="${seed%$'\r'}"
    [[ "$run_id" == "run_id" ]] && continue
    [[ ",$section_filter," == *",$section,"* ]] || continue
    [[ ",$seeds_filter," == *",$seed,"* ]] || continue
    main_wait_slot || failed=1
    main_run_one "$scenario" "$algorithm" "$seed" &
  done <"$MAIN_ROOT/config/run_manifest.csv"
  while (( $(jobs -pr | wc -l) )); do
    wait -n || failed=1
  done
  return "$failed"
}

main_run_explicit() {
  local failed=0 item scenario algorithm seed
  for item in "$@"; do
    IFS=: read -r scenario algorithm seed <<<"$item"
    main_wait_slot || failed=1
    main_run_one "$scenario" "$algorithm" "$seed" &
  done
  while (( $(jobs -pr | wc -l) )); do
    wait -n || failed=1
  done
  return "$failed"
}
