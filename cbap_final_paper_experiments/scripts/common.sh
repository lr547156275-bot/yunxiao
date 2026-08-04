#!/usr/bin/env bash
set -uo pipefail

FINAL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$FINAL_ROOT/.." && pwd)"
SIM_ROOT="$REPO_ROOT/simulation"
MAX_JOBS="${MAX_JOBS:-4}"
MIN_FREE_GB="${MIN_FREE_GB:-5}"
KEEP_RAW="${KEEP_RAW:-0}"
RUN_TIMEOUT_MIN="${RUN_TIMEOUT_MIN:-180}"
export NS_LOG=""
ulimit -c 0

require_metric_gate() {
  local gate="$REPO_ROOT/cbap_final_metric_pipeline/reports/metric_pipeline_selftest.md"
  [[ -f "$gate" ]] && grep -q '^METRIC_PIPELINE_PASS' "$gate" || {
    echo "REFUSE: corrected metric pipeline gate is not PASS" >&2
    return 2
  }
}

disk_check() {
  mkdir -p "$1"
  local free_kb required_kb
  free_kb="$(df -Pk "$1" | awk 'NR==2 {print $4}')"
  required_kb="$(awk -v value="$MIN_FREE_GB" 'BEGIN {printf "%.0f",value*1024*1024}')"
  (( free_kb >= required_kb )) || {
    echo "REFUSE: less than ${MIN_FREE_GB} GiB free at $1" >&2
    return 1
  }
}

write_contract_headers() {
  local d="$1"
  [[ -s "$d/scope_summary.csv" ]] || printf '%s\n' \
    'batch_id,application_ready_ns,decision_complete_ns,decision_delay_ns,flow_count,used_link_count,enabled,reason,triggering_link_count,maximum_pending_count,maximum_oversubscription_ratio' >"$d/scope_summary.csv"
  [[ -s "$d/scope_link_summary.csv" ]] || printf '%s\n' \
    'batch_id,application_ready_ns,newest_summary_sample_ns,newest_summary_delivery_ns,link_id,switch_id,egress_port,pending_count,A_admit_bps,independent_aggregate_bps,oversubscription_bps,oversubscription_ratio,enabled_on_link,pre_release_causal' >"$d/scope_link_summary.csv"
  [[ -s "$d/applied_rate_audit.csv" || -s "$d/applied_rate_audit.csv.gz" ]] || printf '%s\n' \
    'link_id,epoch,C_l,rho_C_l,C_effective_l,planner_grant_sum_bps,target_rate_sum_bps,applied_rate_sum_bps,actual_tx_rate_sum_bps,background_rate_bps,legacy_floor_rate_bps,flows_below_legacy_floor,floor_clamp_count,rate_clamp_delta_sum_bps,zero_grant_flow_count,paused_zero_grant_count,applied_capacity_excess_bps,applied_capacity_violation,actual_arrival_excess_bps' >"$d/applied_rate_audit.csv"
  [[ -s "$d/sender_tx_trace.csv" || -s "$d/sender_tx_trace.csv.gz" ]] || printf '%s\n' \
    'time_ns,event,flow_id,batch_id,packet_seq,wire_bytes,phase,current_rate_bps,target_rate_bps,admit_rate_bps,base_rate_bps,credit_gate_active,credit_remaining_bytes,scheduled_time_ns,actual_send_time_ns,previous_tx_time_ns,expected_gap_ns,actual_gap_ns,reschedule_reason' >"$d/sender_tx_trace.csv"
}

compress_detailed_outputs() {
  local d="$1" file
  [[ "$KEEP_RAW" == 1 ]] && return 0
  for file in selected_link_timeseries.csv selected_flow_timeseries.csv \
              cbap_packet_trace.csv sender_tx_trace.csv \
              cbap_port_summary.csv applied_rate_audit.csv; do
    [[ ! -f "$d/$file" ]] || gzip -f "$d/$file"
  done
}

archive_failed_attempt() {
  local d="$1"
  [[ ! -d "$d" ]] && return 0
  [[ -z "$(find "$d" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] && return 0
  local archive="$d/failed_attempts/attempt_$(date +%Y%m%d_%H%M%S)"
  mkdir -p "$archive"
  find "$d" -mindepth 1 -maxdepth 1 ! -name failed_attempts -exec mv -t "$archive" -- {} +
}

update_meta() {
  python3 - "$1" "$2" "$3" <<'PY'
import json,os,sys,time
p,status,elapsed=sys.argv[1],int(sys.argv[2]),float(sys.argv[3])
m=json.load(open(p)); m.update(exit_status=status,runtime_seconds=elapsed,
 status='finished' if status==0 else 'failed',end_time_unix=time.time())
log=os.path.join(os.path.dirname(p),'stdout.log')
m['log_truncated']='LOG_TRUNCATED' in (open(log,errors='replace').read() if os.path.isfile(log) else '')
q=p+'.tmp'; open(q,'w').write(json.dumps(m,indent=2,sort_keys=True)+'\n');os.replace(q,p)
PY
}

run_one_final() {
  local manifest="$1" output_root="$2" run_id="$3" d start status elapsed
  d="$output_root/$run_id"
  if [[ -f "$d/completed.flag" ]] &&
     python3 "$FINAL_ROOT/scripts/check_outputs.py" "$d" >/dev/null 2>&1; then
    echo "SKIP valid $run_id"
    return 0
  fi
  if [[ -d "$d" ]] && python3 "$FINAL_ROOT/scripts/recover_postprocessing.py" \
      --probe "$d"; then
    echo "SKIP recovered $run_id"
    return 0
  fi
  disk_check "$output_root" || return 1
  archive_failed_attempt "$d"
  mkdir -p "$d"
  python3 "$FINAL_ROOT/scripts/prepare_run.py" "$manifest" "$run_id" "$d" \
    --min-free-gb "$MIN_FREE_GB" || return 1
  python3 - "$d/run_meta.json" <<'PY'
import json,os,sys,time
p=sys.argv[1];m=json.load(open(p));m.update(status='running',start_time_unix=time.time())
q=p+'.tmp';open(q,'w').write(json.dumps(m,indent=2,sort_keys=True)+'\n');os.replace(q,p)
PY
  start="$(date +%s)"
  set +e
  (cd "$SIM_ROOT" && timeout --signal=TERM --kill-after=30s "${RUN_TIMEOUT_MIN}m" \
    python2 ./waf --cwd="$d" --run "scratch/third $d/config.txt") \
      >"$d/stdout.full.log" 2>&1
  status=$?
  set -e
  tail -c 10485760 "$d/stdout.full.log" >"$d/stdout.log"
  elapsed="$(( $(date +%s) - start ))"
  printf '%s\n' "$status" >"$d/exit_status.txt"
  update_meta "$d/run_meta.json" "$status" "$elapsed"
  write_contract_headers "$d"
  if (( status != 0 )); then
    echo "FAIL $run_id exit=$status (diagnostics retained)" >&2
    return "$status"
  fi
  [[ "$KEEP_RAW" == 1 ]] || rm -f "$d/stdout.full.log"
  python3 "$REPO_ROOT/cbap_exp/scripts/collect_run_metrics.py" "$d" || return 1
  python3 "$REPO_ROOT/cbap_exp/scripts/materialize_required_summaries.py" "$d" || return 1
  python3 "$FINAL_ROOT/scripts/materialize_incumbent_summary.py" "$d" || return 1
  write_contract_headers "$d"
  compress_detailed_outputs "$d" || return 1
  python3 "$REPO_ROOT/cbap_final_metric_pipeline/scripts/collect_full_work_metrics.py" \
    --run-dir "$d" --output-dir "$d" || return 1
  python3 "$FINAL_ROOT/scripts/check_outputs.py" --pre-complete "$d" || return 1
  touch "$d/completed.flag"
  echo "PASS $run_id"
}

run_manifest_final() {
  local manifest="$1" output_root="$2" failed=0 run_id
  require_metric_gate || return
  [[ -f "$manifest" ]] || { echo "missing manifest: $manifest" >&2; return 2; }
  trap 'jobs -pr | xargs -r kill; wait; exit 130' INT TERM
  while IFS= read -r run_id; do
    while (( $(jobs -pr | wc -l) >= MAX_JOBS )); do wait -n || failed=1; done
    run_one_final "$manifest" "$output_root" "$run_id" &
  done < <(python3 - "$manifest" <<'PY'
import csv,sys
for row in csv.DictReader(open(sys.argv[1])): print(row['run_id'])
PY
)
  while (( $(jobs -pr | wc -l) )); do wait -n || failed=1; done
  return "$failed"
}
