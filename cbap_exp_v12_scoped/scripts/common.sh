#!/usr/bin/env bash
set -uo pipefail
V12_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."&&pwd)"
REPO_ROOT="$(cd "$V12_ROOT/.."&&pwd)"; SIM_ROOT="$REPO_ROOT/simulation"
MAX_JOBS="${MAX_JOBS:-4}";MIN_FREE_GB="${MIN_FREE_GB:-5}";RUN_TIMEOUT_MIN="${RUN_TIMEOUT_MIN:-60}";KEEP_RAW="${KEEP_RAW:-0}"
export NS_LOG="";ulimit -c 0
disk_check(){ mkdir -p "$1";local free need;free="$(df -Pk "$1"|awk 'NR==2{print $4}')";need="$(awk -v x="$MIN_FREE_GB" 'BEGIN{printf "%.0f",x*1024*1024}')";((free>=need))||{ echo "REFUSE less than $MIN_FREE_GB GiB free" >&2;return 1;};}
finalize_meta(){ python3 - "$1" "$2" "$3" <<'PY'
import csv,json,os,sys,time
d,s,e=sys.argv[1],int(sys.argv[2]),float(sys.argv[3]);p=os.path.join(d,'run_meta.json');m=json.load(open(p));log=open(os.path.join(d,'stdout.log'),errors='replace').read()
m.update(exit_status=s,runtime_seconds=e,end_time_unix=time.time(),status='finished' if s==0 else 'failed',log_truncated='TRUNCATED' in log)
sp=os.path.join(d,'scope_summary.csv');lp=os.path.join(d,'scope_link_summary.csv')
if os.path.isfile(sp):
 rows=list(csv.DictReader(open(sp)))
 if rows:
  enabled=any(int(x['enabled']) for x in rows);m['scope_decision']='ENABLE' if enabled else 'BYPASS';m['scope_reason']=rows[-1]['reason']
q=p+'.tmp';open(q,'w').write(json.dumps(m,indent=2,sort_keys=True)+'\n');os.replace(q,p)
mp=os.path.join(d,'manifest.json');manifest=json.load(open(mp));manifest.update({k:m[k] for k in ('scope_decision','scope_reason') if k in m})
links=list(csv.DictReader(open(lp))) if os.path.isfile(lp) else [];triggers=[x for x in links if int(x.get('enabled_on_link',0))]
if triggers:
 x=max(triggers,key=lambda y:float(y['oversubscription_ratio']));manifest.update(triggering_link=x['link_id'],pending_count_on_triggering_link=int(x['pending_count']),independent_aggregate_rate_bps=int(x['independent_aggregate_bps']),batch_admission_capacity_bps=int(x['A_admit_bps']),oversubscription_ratio=float(x['oversubscription_ratio']))
q=mp+'.tmp';open(q,'w').write(json.dumps(manifest,indent=2,sort_keys=True)+'\n');os.replace(q,mp)
PY
}
empty_scope(){ [[ -s "$1/scope_summary.csv" ]]||echo 'batch_id,application_ready_ns,decision_complete_ns,decision_delay_ns,flow_count,used_link_count,enabled,reason,triggering_link_count,maximum_pending_count,maximum_oversubscription_ratio' >"$1/scope_summary.csv";[[ -s "$1/scope_link_summary.csv" ]]||echo 'batch_id,application_ready_ns,newest_summary_sample_ns,newest_summary_delivery_ns,link_id,switch_id,egress_port,pending_count,A_admit_bps,independent_aggregate_bps,oversubscription_bps,oversubscription_ratio,enabled_on_link,pre_release_causal' >"$1/scope_link_summary.csv";}
run_one(){ local manifest="$1" root="$2" id="$3" scenario algorithm seed dir start status elapsed;read -r scenario algorithm seed < <(python3 - "$manifest" "$id" <<'PY'
import csv,sys
for r in csv.DictReader(open(sys.argv[1])):
 if r['run_id']==sys.argv[2]:print(r['scenario'],r['algorithm_name'],r['seed']);break
else:raise SystemExit('unknown run')
PY
);dir="$root/$scenario/$algorithm/seed_$seed"
 if [[ -f "$dir/completed.flag" ]]&&python3 "$V12_ROOT/scripts/check_outputs.py" "$dir" >/dev/null 2>&1;then echo "SKIP valid $id";return 0;fi
 disk_check "$root"||return;mkdir -p "$dir";python3 "$V12_ROOT/scripts/prepare_run.py" "$manifest" "$id" "$dir" --min-free-gb "$MIN_FREE_GB"||return
 rm -f "$dir/completed.flag" "$dir/exit_status.txt";start="$(date +%s)";set +e
 (cd "$SIM_ROOT"&&timeout --signal=TERM --kill-after=30s "${RUN_TIMEOUT_MIN}m" python2 ./waf --cwd="$dir" --run "scratch/third $dir/config.txt") >"$dir/stdout.full.log" 2>&1;status=$?;set -e
 tail -c 10485760 "$dir/stdout.full.log" >"$dir/stdout.log";[[ "$KEEP_RAW" == 1 ]]||rm -f "$dir/stdout.full.log";elapsed="$(($(date +%s)-start))";echo "$status">"$dir/exit_status.txt";empty_scope "$dir";finalize_meta "$dir" "$status" "$elapsed"
 if ((status!=0));then echo "FAIL $id exit=$status" >&2;return "$status";fi
 python3 "$REPO_ROOT/cbap_exp/scripts/collect_run_metrics.py" "$dir"||return
 python3 "$REPO_ROOT/cbap_exp/scripts/materialize_required_summaries.py" "$dir"||return
 empty_scope "$dir";python3 "$V12_ROOT/scripts/check_outputs.py" --allow-no-complete-flag "$dir"||return;touch "$dir/completed.flag"
 if [[ "$KEEP_RAW" != 1 ]];then for f in selected_link_timeseries.csv selected_flow_timeseries.csv cbap_packet_trace.csv cbap_tx_events.csv;do [[ ! -f "$dir/$f" ]]||gzip -f "$dir/$f";done;fi
 echo "PASS $id";
}
run_manifest(){ local manifest="$1" root="$2" failed=0 id;trap 'jobs -pr|xargs -r kill;wait;exit 130' INT TERM
 while IFS= read -r id;do while (( $(jobs -pr|wc -l)>=MAX_JOBS));do wait -n||failed=1;done;run_one "$manifest" "$root" "$id"&done < <(python3 - "$manifest" <<'PY'
import csv,sys
for r in csv.DictReader(open(sys.argv[1])):print(r['run_id'])
PY
)
 while (( $(jobs -pr|wc -l) ));do wait -n||failed=1;done;return "$failed";
}
