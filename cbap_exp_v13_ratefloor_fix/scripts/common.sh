#!/usr/bin/env bash
set -uo pipefail
V13_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$V13_ROOT/.." && pwd)"
SIM_ROOT="$REPO_ROOT/simulation"
MAX_JOBS="${MAX_JOBS:-1}"
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

write_empty_contracts() {
  local d="$1"
  [[ -s "$d/scope_summary.csv" ]] || echo 'batch_id,application_ready_ns,decision_complete_ns,decision_delay_ns,flow_count,used_link_count,enabled,reason,triggering_link_count,maximum_pending_count,maximum_oversubscription_ratio' > "$d/scope_summary.csv"
  [[ -s "$d/scope_link_summary.csv" ]] || echo 'batch_id,application_ready_ns,newest_summary_sample_ns,newest_summary_delivery_ns,link_id,switch_id,egress_port,pending_count,A_admit_bps,independent_aggregate_bps,oversubscription_bps,oversubscription_ratio,enabled_on_link,pre_release_causal' > "$d/scope_link_summary.csv"
  [[ -s "$d/applied_rate_audit.csv" ]] || echo 'link_id,epoch,C_l,rho_C_l,C_effective_l,planner_grant_sum_bps,target_rate_sum_bps,applied_rate_sum_bps,actual_tx_rate_sum_bps,background_rate_bps,legacy_floor_rate_bps,flows_below_legacy_floor,floor_clamp_count,rate_clamp_delta_sum_bps,zero_grant_flow_count,paused_zero_grant_count,applied_capacity_excess_bps,applied_capacity_violation,actual_arrival_excess_bps' > "$d/applied_rate_audit.csv"
  [[ -s "$d/sender_tx_trace.csv" ]] || echo 'time_ns,event,flow_id,batch_id,packet_seq,wire_bytes,phase,current_rate_bps,target_rate_bps,admit_rate_bps,base_rate_bps,credit_gate_active,credit_remaining_bytes,scheduled_time_ns,actual_send_time_ns,previous_tx_time_ns,expected_gap_ns,actual_gap_ns,reschedule_reason' > "$d/sender_tx_trace.csv"
}

finalize_meta() {
  python3 - "$1" "$2" "$3" <<'PY'
import csv,json,os,sys,time
d,status,elapsed=sys.argv[1],int(sys.argv[2]),float(sys.argv[3])
p=os.path.join(d,'run_meta.json'); m=json.load(open(p))
log=open(os.path.join(d,'stdout.log'),errors='replace').read()
m.update(exit_status=status,runtime_seconds=elapsed,end_time_unix=time.time(),
         status='finished' if status==0 else 'failed',
         log_truncated=('TRUNCATED' in log))
m.setdefault('algorithm',m.get('algorithm_name','unknown'))
sp=os.path.join(d,'scope_summary.csv')
if os.path.isfile(sp):
 rows=list(csv.DictReader(open(sp)))
 if rows:
  enabled=any(int(x.get('enabled',0)) for x in rows)
  m['scope_decision']='ENABLE' if enabled else 'BYPASS'
  m['scope_reason']=rows[-1].get('reason','')
q=p+'.tmp'; open(q,'w').write(json.dumps(m,indent=2,sort_keys=True)+'\n'); os.replace(q,p)
mp=os.path.join(d,'manifest.json'); manifest=json.load(open(mp))
for k in ('scope_decision','scope_reason'):
 if k in m: manifest[k]=m[k]
q=mp+'.tmp'; open(q,'w').write(json.dumps(manifest,indent=2,sort_keys=True)+'\n'); os.replace(q,mp)
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
  if [[ -f "$d/completed.flag" ]] && python3 "$V13_ROOT/scripts/check_outputs.py" "$d" >/dev/null 2>&1; then
    echo "SKIP valid $run_id"
    return 0
  fi
  disk_check "$output_root" || return 1
  mkdir -p "$d"
  python3 "$V13_ROOT/scripts/prepare_run.py" "$manifest" "$run_id" "$d" --min-free-gb "$MIN_FREE_GB" || return 1
  rm -f "$d/completed.flag" "$d/exit_status.txt"
  start="$(date +%s)"; set +e
  (cd "$SIM_ROOT" && timeout --signal=TERM --kill-after=30s "${RUN_TIMEOUT_MIN}m" \
    python2 ./waf --cwd="$d" --run "scratch/third $d/config.txt") > "$d/stdout.full.log" 2>&1
  status=$?; set -e
  tail -c 10485760 "$d/stdout.full.log" > "$d/stdout.log"
  [[ "$KEEP_RAW" == 1 ]] || rm -f "$d/stdout.full.log"
  elapsed="$(( $(date +%s)-start ))"
  echo "$status" > "$d/exit_status.txt"
  write_empty_contracts "$d"
  finalize_meta "$d" "$status" "$elapsed"
  if (( status != 0 )); then echo "FAIL $run_id exit=$status" >&2; return "$status"; fi
  python3 "$REPO_ROOT/cbap_exp/scripts/collect_run_metrics.py" "$d" || return 1
  python3 "$REPO_ROOT/cbap_exp/scripts/materialize_required_summaries.py" "$d" || return 1
  write_empty_contracts "$d"
  python3 "$V13_ROOT/scripts/check_outputs.py" --allow-no-complete-flag "$d" || return 1
  touch "$d/completed.flag"
  if [[ "$KEEP_RAW" != 1 ]]; then
    for f in selected_link_timeseries.csv selected_flow_timeseries.csv cbap_packet_trace.csv; do
      [[ ! -f "$d/$f" ]] || gzip -f "$d/$f"
    done
  fi
  echo "PASS $run_id"
}

run_manifest() {
  local manifest="$1" output_root="$2" failed=0 run_id
  trap 'jobs -pr | xargs -r kill; wait; exit 130' INT TERM
  while IFS= read -r run_id; do
    while (( $(jobs -pr | wc -l) >= MAX_JOBS )); do wait -n || failed=1; done
    run_one "$manifest" "$output_root" "$run_id" &
  done < <(python3 - "$manifest" <<'PY'
import csv,sys
for row in csv.DictReader(open(sys.argv[1])): print(row['run_id'])
PY
)
  while (( $(jobs -pr | wc -l) )); do wait -n || failed=1; done
  return "$failed"
}
