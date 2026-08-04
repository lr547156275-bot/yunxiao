#!/usr/bin/env bash
set -uo pipefail

CBAP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SIM_ROOT="$(cd "$CBAP_ROOT/../simulation" && pwd)"
RUN_ROOT="${RUN_ROOT:-$CBAP_ROOT/runs}"
MAX_JOBS="${MAX_JOBS:-4}"
MIN_FREE_GB="${MIN_FREE_GB:-5}"
RUN_TIMEOUT_MIN="${RUN_TIMEOUT_MIN:-60}"
KEEP_RAW="${KEEP_RAW:-0}"
export NS_LOG=""
ulimit -c 0

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

update_meta() {
  local path="$1" status="$2" elapsed="$3"
  python3 - "$path" "$status" "$elapsed" <<'PY'
import json, os, sys, time
path, status, elapsed = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
data = json.load(open(path))
log_path = os.path.join(os.path.dirname(path), "stdout.log")
truncated = False
if os.path.isfile(log_path):
    text = open(log_path, errors="replace").read()
    truncated = ("LOG_TRUNCATED" in text or
                 "CBAP_PACKET_TRACE_TRUNCATED" in text)
data.update({"exit_status": status, "runtime_seconds": elapsed,
             "end_time_unix": time.time(),
             "status": "finished" if status == 0 else "failed",
             "log_truncated": truncated})
tmp = path + ".tmp"
with open(tmp, "w") as out:
    json.dump(data, out, indent=2, sort_keys=True); out.write("\n")
os.replace(tmp, path)
PY
}

run_one() {
  local run_id="$1"
  local scenario subcase algorithm seed run_dir start end elapsed status
  IFS=$'\t' read -r scenario subcase algorithm seed < <(
    python3 - "$CBAP_ROOT/config/run_manifest.csv" "$run_id" <<'PY'
import csv, sys
for row in csv.DictReader(open(sys.argv[1])):
    if row["run_id"] == sys.argv[2]:
        print("\t".join((row["scenario"], row["subcase"],
                        row["algorithm"], row["seed"])))
        break
else:
    raise SystemExit("unknown run id")
PY
  )
  run_dir="$RUN_ROOT/$scenario/$subcase/$algorithm/seed_$seed"
  if [[ -f "$run_dir/completed.flag" ]] &&
      python3 "$CBAP_ROOT/scripts/check_outputs.py" "$run_dir" \
        >/dev/null 2>&1; then
    echo "SKIP valid $run_id"
    return 0
  fi
  disk_check || return 1
  mkdir -p "$run_dir"
  python3 "$CBAP_ROOT/scripts/prepare_run.py" \
    "$run_id" "$run_dir" --min-free-gb "$MIN_FREE_GB" || return
  rm -f "$run_dir/completed.flag" "$run_dir/exit_status.txt" \
    "$run_dir/result.json"
  python3 - "$run_dir/run_meta.json" <<'PY'
import json, os, sys, time
path=sys.argv[1]; data=json.load(open(path))
data.update({"start_time_unix":time.time(), "status":"running"})
tmp=path+".tmp"
with open(tmp,"w") as out:
    json.dump(data,out,indent=2,sort_keys=True); out.write("\n")
os.replace(tmp,path)
PY
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
  end="$(date +%s)"; elapsed="$((end-start))"
  printf '%s\n' "$status" >"$run_dir/exit_status.txt"
  printf '%s\n' "$elapsed" >"$run_dir/runtime_seconds.txt"
  update_meta "$run_dir/run_meta.json" "$status" "$elapsed"
  if (( status != 0 )); then
    echo "FAIL $run_id exit=$status (diagnostics retained)" >&2
    return "$status"
  fi
  python3 "$CBAP_ROOT/scripts/collect_run_metrics.py" "$run_dir" || return
  python3 "$CBAP_ROOT/scripts/materialize_required_summaries.py" \
    "$run_dir" || return
  python3 "$CBAP_ROOT/scripts/augment_packet_trace.py" "$run_dir" || return
  python3 "$CBAP_ROOT/scripts/check_outputs.py" \
    --allow-no-complete-flag "$run_dir" || return
  touch "$run_dir/completed.flag"
  if [[ "$KEEP_RAW" != "1" ]]; then
    local name
    for name in selected_link_timeseries.csv \
                selected_flow_timeseries.csv \
                cbap_packet_trace.csv; do
      [[ ! -f "$run_dir/$name" ]] || gzip -f "$run_dir/$name"
    done
  fi
  echo "PASS $run_id"
}

wait_slot() {
  while (( $(jobs -pr | wc -l) >= MAX_JOBS )); do
    wait -n || return 1
  done
}

run_ids() {
  local failed=0 run_id
  trap 'jobs -pr | xargs -r kill; wait; exit 130' INT TERM
  for run_id in "$@"; do
    wait_slot || failed=1
    run_one "$run_id" &
  done
  while (( $(jobs -pr | wc -l) )); do
    wait -n || failed=1
  done
  return "$failed"
}

run_manifest() {
  local seeds="${SEEDS:-1,2,3}" failed=0 run_id seed
  while IFS=, read -r run_id _ _ _ _ seed _; do
    seed="${seed%$'\r'}"
    [[ "$run_id" == "run_id" ]] && continue
    [[ ",$seeds," == *",$seed,"* ]] || continue
    wait_slot || failed=1
    run_one "$run_id" &
  done <"$CBAP_ROOT/config/run_manifest.csv"
  while (( $(jobs -pr | wc -l) )); do
    wait -n || failed=1
  done
  return "$failed"
}
