#!/usr/bin/env bash
set -uo pipefail

CLOS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SIM_ROOT="$(cd "$CLOS_ROOT/../.." && pwd)"
RUN_ROOT="${RUN_ROOT:-$CLOS_ROOT/runs}"
JOBS="${JOBS:-1}"
SEEDS="${SEEDS:-}"
MIN_FREE_GB="${MIN_FREE_GB:-5}"
KEEP_RAW="${KEEP_RAW:-0}"
RUN_TIMEOUT_MIN="${RUN_TIMEOUT_MIN:-180}"
FORCE_RERUN="${FORCE_RERUN:-0}"
export NS_LOG=""
ulimit -c 0

clos_require_regression() {
  [[ -f "$CLOS_ROOT/single_bottleneck_regression/PASS.flag" ]] || {
    echo "REFUSE Clos run: first run ./bop_exp/clos_v1/run_single_bottleneck_regression.sh" >&2
    return 2
  }
}

clos_disk_check() {
  mkdir -p "$RUN_ROOT"
  local free_kb required_kb
  free_kb="$(df -Pk "$RUN_ROOT" | awk 'NR==2 {print $4}')"
  required_kb="$(awk -v v="$MIN_FREE_GB" 'BEGIN {printf "%.0f",v*1024*1024}')"
  (( free_kb >= required_kb )) || {
    echo "REFUSE less than ${MIN_FREE_GB} GiB free at $RUN_ROOT" >&2
    return 1
  }
}

clos_update_meta() {
  local path="$1" status="$2" elapsed="$3"
  python3 - "$path" "$status" "$elapsed" <<'PY'
import json,os,sys,time
p,status,elapsed=sys.argv[1],int(sys.argv[2]),float(sys.argv[3])
d=json.load(open(p)); d.update({
 "exit_status":status,"runtime_seconds":elapsed,"end_time_unix":time.time(),
 "status":"finished" if status == 0 else "failed"})
t=p+".tmp"
with open(t,"w") as h: json.dump(d,h,indent=2,sort_keys=True); h.write("\n")
os.replace(t,p)
PY
}

clos_clear_outputs() {
  local dir="$1" name
  for name in completed.flag exit_status.txt runtime_seconds.txt run.log \
      flow_summary.csv round_summary.csv feedback_summary.csv \
      controller_summary.csv group_round_summary.csv flow_plan.csv \
      flow_plan.csv.gz selected_link_timeseries.csv \
      selected_link_timeseries.csv.gz selected_flow_timeseries.csv \
      selected_flow_timeseries.csv.gz pfc_events.csv \
      bop_qb_group_decisions.csv bop_multilink_group_decisions.csv \
      bop_multilink_link_constraints.csv run_metrics.csv \
      per_link_metrics.csv collective_metrics.csv; do
    rm -f "$dir/$name"
  done
}

clos_run_one() {
  local run_id="$1"
  local run_dir="$RUN_ROOT/$run_id"
  local start end elapsed status
  if [[ -f "$run_dir/completed.flag" ]] &&
      python3 "$CLOS_ROOT/scripts/check_clos_outputs.py" "$run_dir" \
        >/dev/null 2>&1; then
    echo "SKIP valid $run_id"
    return 0
  fi
  if [[ -f "$run_dir/completed.flag" && "$FORCE_RERUN" != "1" ]]; then
    echo "REFUSE invalid completed run; set FORCE_RERUN=1: $run_id" >&2
    return 2
  fi
  clos_disk_check || return
  mkdir -p "$run_dir"
  clos_clear_outputs "$run_dir"
  python3 "$CLOS_ROOT/scripts/prepare_clos_run.py" "$run_id" "$run_dir" \
    --min-free-gb "$MIN_FREE_GB" || return
  python3 - "$run_dir/run_meta.json" <<'PY'
import json,os,sys,time
p=sys.argv[1]; d=json.load(open(p)); d.update(
 {"status":"running","start_time_unix":time.time()})
t=p+".tmp"
with open(t,"w") as h: json.dump(d,h,indent=2,sort_keys=True); h.write("\n")
os.replace(t,p)
PY
  start="$(date +%s)"
  set +e
  (
    cd "$SIM_ROOT" || exit 125
    timeout --signal=TERM --kill-after=30s "${RUN_TIMEOUT_MIN}m" \
      python2 ./waf --cwd="$run_dir" \
        --run "scratch/third $run_dir/config.txt"
  ) 2>&1 | tail -c 10485760 >"$run_dir/run.log"
  status="${PIPESTATUS[0]}"
  set -e
  end="$(date +%s)"; elapsed="$((end-start))"
  printf '%s\n' "$status" >"$run_dir/exit_status.txt"
  printf '%s\n' "$elapsed" >"$run_dir/runtime_seconds.txt"
  clos_update_meta "$run_dir/run_meta.json" "$status" "$elapsed"
  if (( status != 0 )); then
    echo "FAIL $run_id exit=$status (raw retained)" >&2
    return "$status"
  fi
  python3 "$CLOS_ROOT/scripts/parse_clos_results.py" --run "$run_dir" || {
    echo "FAIL metrics $run_id (raw retained)" >&2; return 1; }
  python3 "$CLOS_ROOT/scripts/check_clos_outputs.py" \
    --pre-complete "$run_dir" || {
    echo "FAIL validation $run_id (raw retained)" >&2; return 1; }
  touch "$run_dir/completed.flag"
  if [[ "$KEEP_RAW" != "1" ]]; then
    local name
    for name in selected_flow_timeseries.csv selected_link_timeseries.csv \
                flow_plan.csv; do
      [[ ! -f "$run_dir/$name" ]] || gzip -f "$run_dir/$name"
    done
    gzip -f "$run_dir/run.log"
  fi
  echo "PASS $run_id"
}

clos_wait_slot() {
  while (( $(jobs -pr | wc -l) >= JOBS )); do wait -n || return 1; done
}

clos_run_manifest() {
  local seeds_filter="$1" section_filter="${2:-all}" failed=0
  local run_id section scenario topology collective participants message algorithm cc_mode seed
  clos_require_regression || return
  trap 'jobs -pr | xargs -r kill; wait; exit 130' INT TERM
  while IFS=, read -r run_id section scenario topology collective participants message algorithm cc_mode seed; do
    seed="${seed%$'\r'}"
    [[ "$run_id" == "run_id" ]] && continue
    [[ ",$seeds_filter," == *",$seed,"* ]] || continue
    [[ "$section_filter" == "all" ||
       ",$section_filter," == *",$section,"* ]] || continue
    clos_wait_slot || failed=1
    clos_run_one "$run_id" &
  done <"$CLOS_ROOT/config/run_manifest.csv"
  while (( $(jobs -pr | wc -l) )); do wait -n || failed=1; done
  return "$failed"
}

clos_run_ids() {
  local failed=0 run_id
  clos_require_regression || return
  for run_id in "$@"; do
    clos_wait_slot || failed=1
    clos_run_one "$run_id" &
  done
  while (( $(jobs -pr | wc -l) )); do wait -n || failed=1; done
  return "$failed"
}
