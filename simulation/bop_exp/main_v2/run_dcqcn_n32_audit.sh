#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SIM_ROOT="$(cd "$ROOT/../.." && pwd)"
RUN_ROOT="${RUN_ROOT:-$ROOT/audit_runs}"
MIN_FREE_GB="${MIN_FREE_GB:-5}"
RUN_TIMEOUT_MIN="${RUN_TIMEOUT_MIN:-60}"
RUN_DIR="$RUN_ROOT/dcqcn_n32_current/dcqcn/seed_1"
export NS_LOG=""
ulimit -c 0

mkdir -p "$RUN_DIR"
free_kb="$(df -Pk "$RUN_ROOT" | awk 'NR==2 {print $4}')"
required_kb="$(awk -v value="$MIN_FREE_GB" \
  'BEGIN {printf "%.0f", value*1024*1024}')"
(( free_kb >= required_kb )) || {
  echo "REFUSE less than ${MIN_FREE_GB} GiB free" >&2
  exit 1
}
python3 "$ROOT/../main_v1/scripts/prepare_main_run.py" \
  n32_64k_g50 dcqcn 1 "$RUN_DIR" --min-free-gb "$MIN_FREE_GB"
set +e
(
  cd "$SIM_ROOT"
  timeout --signal=TERM --kill-after=30s "${RUN_TIMEOUT_MIN}m" \
    python2 ./waf --cwd="$RUN_DIR" \
      --run "scratch/third $RUN_DIR/config.txt"
) 2>&1 | tail -c 10485760 >"$RUN_DIR/stdout.log"
status="${PIPESTATUS[0]}"
set -e
printf '%s\n' "$status" >"$RUN_DIR/exit_status.txt"
if (( status != 0 )); then
  echo "FAIL dcqcn_n32_current exit=$status" >&2
  exit "$status"
fi
python3 "$ROOT/../main_v1/scripts/collect_run_metrics.py" "$RUN_DIR"
python3 - "$RUN_DIR/run_meta.json" "$status" <<'PY'
import json, os, sys, time
path, status = sys.argv[1], int(sys.argv[2])
data=json.load(open(path))
data.update({"exit_status": status, "status": "finished",
             "end_time_unix": time.time(),
             "audit_name": "dcqcn_n32_current"})
tmp=path+".tmp"
with open(tmp,"w") as out:
    json.dump(data,out,indent=2,sort_keys=True); out.write("\n")
os.replace(tmp,path)
PY
touch "$RUN_DIR/completed.flag"
python3 "$ROOT/scripts/build_corrected_analysis.py"
echo "PASS dcqcn_n32_current seed=1"
