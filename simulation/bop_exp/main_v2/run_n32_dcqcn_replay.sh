#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SIM_ROOT="$(cd "$ROOT/../.." && pwd)"
RUN_ROOT="${RUN_ROOT:-$ROOT/n32_dcqcn_replay}"
JOBS="${JOBS:-1}"
MIN_FREE_GB="${MIN_FREE_GB:-5}"
RUN_TIMEOUT_MIN="${RUN_TIMEOUT_MIN:-60}"
KEEP_RAW="${KEEP_RAW:-0}"
export NS_LOG=""
ulimit -c 0

if [[ "$JOBS" != "1" ]]; then
  echo "n32 deterministic replay is intentionally serialized; set JOBS=1" >&2
  exit 2
fi

python3 "$ROOT/scripts/check_n32_dcqcn_replay.py" --static

disk_check() {
  mkdir -p "$RUN_ROOT"
  local free_kb required_kb
  free_kb="$(df -Pk "$RUN_ROOT" | awk 'NR==2 {print $4}')"
  required_kb="$(awk -v value="$MIN_FREE_GB" \
    'BEGIN {printf "%.0f", value*1024*1024}')"
  (( free_kb >= required_kb )) || {
    echo "REFUSE less than ${MIN_FREE_GB} GiB free" >&2
    return 1
  }
}

copy_exact_inputs() {
  local seed="$1" source="$2" run_dir="$3"
  mkdir -p "$run_dir"
  local name
  for name in topology.txt flow.txt rounds.txt fixed_paths.txt trace.txt \
      config.txt scenario_meta.json; do
    cp -- "$source/$name" "$run_dir/$name"
  done
  cp -- "$source/run_meta.json" "$run_dir/run_meta.json"
  python3 - "$run_dir/run_meta.json" "$seed" "$source" <<'PY'
import json, os, sys, time
path, seed, source = sys.argv[1], int(sys.argv[2]), sys.argv[3]
data = json.load(open(path))
data.update({
    "run_id": "n32_64k_g50__dcqcn__seed%d__deterministic_replay" % seed,
    "replay_of": source,
    "deterministic_replay": True,
    "legacy_213us_excluded": True,
    "status": "prepared",
    "exit_status": None,
    "start_time_unix": time.time(),
})
tmp = path + ".tmp"
with open(tmp, "w") as stream:
    json.dump(data, stream, indent=2, sort_keys=True)
    stream.write("\n")
os.replace(tmp, path)
PY
}

run_one() {
  local seed="$1"
  local source="$SIM_ROOT/bop_exp/main_v1/runs/n32_64k_g50/dcqcn/seed_$seed"
  local run_dir="$RUN_ROOT/seed_$seed"
  if [[ -f "$run_dir/completed.flag" ]] &&
      python3 "$ROOT/scripts/check_n32_dcqcn_replay.py" \
        --run "$run_dir" --seed "$seed" >/dev/null 2>&1; then
    echo "SKIP valid n32_64k_g50 dcqcn seed=$seed"
    return 0
  fi
  disk_check
  mkdir -p "$run_dir"
  rm -f -- "$run_dir/completed.flag" "$run_dir/exit_status.txt" \
    "$run_dir/stdout.log" "$run_dir/fct.txt" "$run_dir/pfc.txt" \
    "$run_dir/flow_summary.csv" "$run_dir/round_summary.csv" \
    "$run_dir/feedback_summary.csv" "$run_dir/controller_summary.csv" \
    "$run_dir/group_round_summary.csv" "$run_dir/flow_plan.csv" \
    "$run_dir/bop_qb_group_decisions.csv" \
    "$run_dir/selected_flow_timeseries.csv" \
    "$run_dir/selected_link_timeseries.csv" \
    "$run_dir/raw_wire_size_summary.csv" "$run_dir/queue_summary.csv" \
    "$run_dir/congestion_summary.csv" "$run_dir/wire_summary.csv" \
    "$run_dir/algorithm_summary.csv"
  copy_exact_inputs "$seed" "$source" "$run_dir"
  python3 "$ROOT/scripts/check_n32_dcqcn_replay.py" \
    --run "$run_dir" --seed "$seed" --inputs-only
  set +e
  (
    cd "$SIM_ROOT"
    timeout --signal=TERM --kill-after=30s "${RUN_TIMEOUT_MIN}m" \
      python2 ./waf --cwd="$run_dir" \
        --run "scratch/third $run_dir/config.txt"
  ) 2>&1 | tail -c 10485760 >"$run_dir/stdout.log"
  local status="${PIPESTATUS[0]}"
  set -e
  printf '%s\n' "$status" >"$run_dir/exit_status.txt"
  python3 - "$run_dir/run_meta.json" "$status" <<'PY'
import json, os, sys, time
path, status = sys.argv[1], int(sys.argv[2])
data = json.load(open(path))
data.update({
    "exit_status": status,
    "status": "finished" if status == 0 else "failed",
    "end_time_unix": time.time(),
})
tmp = path + ".tmp"
with open(tmp, "w") as stream:
    json.dump(data, stream, indent=2, sort_keys=True)
    stream.write("\n")
os.replace(tmp, path)
PY
  if (( status != 0 )); then
    echo "FAIL n32_64k_g50 dcqcn seed=$seed exit=$status" >&2
    return "$status"
  fi
  python3 "$ROOT/../main_v1/scripts/collect_run_metrics.py" "$run_dir"
  touch "$run_dir/completed.flag"
  if ! python3 "$ROOT/scripts/check_n32_dcqcn_replay.py" \
      --run "$run_dir" --seed "$seed"; then
    rm -f -- "$run_dir/completed.flag"
    echo "FAIL deterministic comparison seed=$seed" >&2
    return 1
  fi
  if [[ "$KEEP_RAW" != "1" ]]; then
    for name in selected_flow_timeseries.csv selected_link_timeseries.csv \
        raw_wire_size_summary.csv flow_plan.csv; do
      if [[ -f "$run_dir/$name" ]] && gzip -f -- "$run_dir/$name"; then
        :
      fi
    done
  fi
  echo "PASS n32_64k_g50 dcqcn seed=$seed"
}

for seed in 1 2 3; do
  run_one "$seed"
done
python3 "$ROOT/scripts/check_n32_dcqcn_replay.py" --runs "$RUN_ROOT"
python3 "$ROOT/scripts/analyze_n32_dcqcn_replay.py" --runs "$RUN_ROOT"
