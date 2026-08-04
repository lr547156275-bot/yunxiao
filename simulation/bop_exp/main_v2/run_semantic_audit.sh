#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SIM_ROOT="$(cd "$ROOT/../.." && pwd)"
RUN_ROOT="${RUN_ROOT:-$ROOT/audit_runs}"
JOBS="${JOBS:-1}"
MIN_FREE_GB="${MIN_FREE_GB:-5}"
RUN_TIMEOUT_MIN="${RUN_TIMEOUT_MIN:-60}"
export NS_LOG=""
ulimit -c 0

python3 "$ROOT/scripts/check_semantic_audit.py" --static

if [[ "$JOBS" != "1" ]]; then
  echo "PFC semantic audit is intentionally serialized; set JOBS=1" >&2
  exit 2
fi

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

run_one() {
  local scenario="$1" algorithm="$2"
  local run_dir="$RUN_ROOT/$scenario/$algorithm/seed_1"
  if [[ -f "$run_dir/completed.flag" ]] &&
      python3 "$ROOT/scripts/check_semantic_audit.py" \
        --run "$run_dir" >/dev/null 2>&1; then
    echo "SKIP valid $scenario $algorithm seed=1"
    return 0
  fi
  disk_check
  mkdir -p "$run_dir"
  python3 "$ROOT/scripts/prepare_semantic_audit.py" \
    "$scenario" "$algorithm" "$run_dir" --min-free-gb "$MIN_FREE_GB"
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
data=json.load(open(path))
data.update({"exit_status": status, "status": "finished" if status == 0 else
             "failed", "end_time_unix": time.time()})
tmp=path+".tmp"
with open(tmp,"w") as out:
    json.dump(data,out,indent=2,sort_keys=True); out.write("\n")
os.replace(tmp,path)
PY
  if (( status != 0 )); then
    echo "FAIL $scenario $algorithm seed=1 exit=$status" >&2
    return "$status"
  fi
  python3 "$ROOT/../main_v1/scripts/collect_run_metrics.py" "$run_dir"
  touch "$run_dir/completed.flag"
  echo "PASS $scenario $algorithm seed=1"
}

matrix=(
  "msg_4m_n16_g50:open_loop_pfc_configured"
  "msg_4m_n16_g50:open_loop_pfc_disabled"
  "msg_64k_n16_g50:open_loop_pfc_configured"
  "msg_64k_n16_g50:open_loop_pfc_disabled"
  "msg_64k_n16_g50:dcqcn"
  "msg_64k_n16_g50:hpcc_int"
  "msg_64k_n16_g50:bop_qb"
  "n64_64k_g50:open_loop_pfc_configured"
  "n64_64k_g50:open_loop_pfc_disabled"
)
for item in "${matrix[@]}"; do
  IFS=: read -r scenario algorithm <<<"$item"
  run_one "$scenario" "$algorithm"
done
python3 "$ROOT/scripts/check_semantic_audit.py" --runs "$RUN_ROOT"
python3 "$ROOT/scripts/analyze_semantic_audit.py"
