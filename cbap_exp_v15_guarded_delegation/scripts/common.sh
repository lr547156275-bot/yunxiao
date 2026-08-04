#!/usr/bin/env bash
set -uo pipefail
V15_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$V15_ROOT/.." && pwd)"
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
import json,os,sys,time
d,status,elapsed=sys.argv[1],int(sys.argv[2]),float(sys.argv[3])
p=os.path.join(d,'run_meta.json'); m=json.load(open(p))
log=open(os.path.join(d,'run.log'),errors='replace').read()
m.update(exit_status=status,runtime_seconds=elapsed,end_time_unix=time.time(),
         status='finished' if status==0 else 'failed',ns3_executed=True,
         log_truncated=('TRUNCATED' in log))
q=p+'.tmp'; open(q,'w').write(json.dumps(m,indent=2,sort_keys=True)+'\n')
os.replace(q,p)
PY
}

run_one() {
  local manifest="$1" output_root="$2" run_id="$3"
  local scenario algorithm seed d start status elapsed
  read -r scenario algorithm seed < <(python3 - "$manifest" "$run_id" <<'PY'
import csv,sys
for row in csv.DictReader(open(sys.argv[1])):
 if row['run_id']==sys.argv[2]:
  print(row['scenario'],row['algorithm_name'],row['seed']); break
else: raise SystemExit('unknown run')
PY
)
  d="$output_root/$scenario/$algorithm/seed_$seed"
  if [[ -f "$d/completed.flag" ]] && \
      python3 "$V15_ROOT/scripts/check_outputs.py" "$d" >/dev/null 2>&1; then
    echo "SKIP valid $run_id"
    return 0
  fi
  disk_check "$output_root" || return 1
  mkdir -p "$d"
  python3 "$V15_ROOT/scripts/prepare_run.py" "$manifest" "$run_id" "$d" \
    --min-free-gb "$MIN_FREE_GB" || return 1
  rm -f "$d/completed.flag" "$d/exit_status.txt"
  start="$(date +%s)"; set +e
  (cd "$SIM_ROOT" && timeout --signal=TERM --kill-after=30s \
    "${RUN_TIMEOUT_MIN}m" python2 ./waf --cwd="$d" \
    --run "scratch/third $d/config.txt") > "$d/run.full.log" 2>&1
  status=$?; set -e
  tail -c 10485760 "$d/run.full.log" > "$d/run.log"
  cp "$d/run.log" "$d/stdout.log"
  [[ "$KEEP_RAW" == 1 ]] || rm -f "$d/run.full.log"
  elapsed="$(( $(date +%s)-start ))"
  echo "$status" > "$d/exit_status.txt"
  finalize_meta "$d" "$status" "$elapsed"
  if (( status != 0 )); then
    echo "FAIL $run_id exit=$status (diagnostics retained)" >&2
    return "$status"
  fi
  python3 "$V15_ROOT/scripts/collect_run_metrics.py" "$d" || return 1
  python3 "$REPO_ROOT/cbap_exp/scripts/materialize_required_summaries.py" "$d" || return 1
  python3 "$V15_ROOT/scripts/materialize_v15_summaries.py" "$d" || return 1
  python3 "$V15_ROOT/scripts/check_outputs.py" --allow-no-complete-flag "$d" || return 1
  touch "$d/completed.flag"
  if [[ "$KEEP_RAW" != 1 ]]; then
    for f in selected_link_timeseries.csv selected_flow_timeseries.csv \
      cbap_packet_trace.csv; do
      [[ ! -f "$d/$f" ]] || gzip -f "$d/$f"
    done
  fi
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
import csv,sys
for row in csv.DictReader(open(sys.argv[1])): print(row['run_id'])
PY
)
  while (( $(jobs -pr | wc -l) )); do wait -n || failed=1; done
  return "$failed"
}
