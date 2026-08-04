#!/usr/bin/env bash
set -uo pipefail
V11_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$V11_ROOT/.." && pwd)"; SIM_ROOT="$REPO_ROOT/simulation"
MAX_JOBS="${MAX_JOBS:-4}"; MIN_FREE_GB="${MIN_FREE_GB:-5}"; RUN_TIMEOUT_MIN="${RUN_TIMEOUT_MIN:-60}"; KEEP_RAW="${KEEP_RAW:-0}"
export NS_LOG=""; ulimit -c 0
disk_check(){ mkdir -p "$1"; local free need; free="$(df -Pk "$1"|awk 'NR==2{print $4}')"; need="$(awk -v x="$MIN_FREE_GB" 'BEGIN{printf "%.0f",x*1024*1024}')"; ((free>=need)) || { echo "REFUSE less than $MIN_FREE_GB GiB free" >&2; return 1; }; }
update_meta(){ python3 - "$1" "$2" "$3" <<'PY'
import json,os,sys,time
p,s,e=sys.argv[1],int(sys.argv[2]),float(sys.argv[3]); d=json.load(open(p)); log=os.path.join(os.path.dirname(p),'stdout.log'); t=open(log,errors='replace').read() if os.path.isfile(log) else ''
d.update(exit_status=s,runtime_seconds=e,end_time_unix=time.time(),status='finished' if s==0 else 'failed',log_truncated='TRUNCATED' in t)
q=p+'.tmp'; open(q,'w').write(json.dumps(d,indent=2,sort_keys=True)+'\n'); os.replace(q,p)
PY
}
run_one(){ local manifest="$1" root="$2" id="$3" victim="${4:-0}" info scenario subcase algorithm seed dir start status elapsed
 info="$(python3 - "$manifest" "$id" <<'PY'
import csv,sys
for r in csv.DictReader(open(sys.argv[1])):
 if r['run_id']==sys.argv[2]: print('\t'.join((r.get('scenario','victim_calibration'),r['subcase'],r['algorithm_name'],r['seed'])));break
else:raise SystemExit('unknown run')
PY
)"; IFS=$'\t' read -r scenario subcase algorithm seed <<<"$info"; dir="$root/$scenario/$subcase/$algorithm/seed_$seed"
 if [[ -f "$dir/completed.flag" ]] && python3 "$V11_ROOT/scripts/check_outputs.py" "$dir" >/dev/null 2>&1;then echo "SKIP valid $id";return 0;fi
 disk_check "$root"||return; mkdir -p "$dir"; local args=(); [[ "$victim" == 1 ]]&&args+=(--victim)
 python3 "$V11_ROOT/scripts/prepare_run.py" "$manifest" "$id" "$dir" "${args[@]}" --min-free-gb "$MIN_FREE_GB"||return
 rm -f "$dir/completed.flag" "$dir/exit_status.txt"; start="$(date +%s)"; set +e
 (cd "$SIM_ROOT"&&timeout --signal=TERM --kill-after=30s "${RUN_TIMEOUT_MIN}m" python2 ./waf --cwd="$dir" --run "scratch/third $dir/config.txt") 2>&1|tail -c 10485760 >"$dir/stdout.log"; status="${PIPESTATUS[0]}";set -e
 elapsed="$(($(date +%s)-start))"; echo "$status">"$dir/exit_status.txt";update_meta "$dir/run_meta.json" "$status" "$elapsed"
 if ((status!=0));then echo "FAIL $id exit=$status" >&2;return "$status";fi
 python3 "$REPO_ROOT/cbap_exp/scripts/collect_run_metrics.py" "$dir"||return
 python3 "$REPO_ROOT/cbap_exp/scripts/materialize_required_summaries.py" "$dir"||return
 python3 "$V11_ROOT/scripts/check_outputs.py" --allow-no-complete-flag "$dir"||return;touch "$dir/completed.flag"
 if [[ "$KEEP_RAW" != 1 ]];then for f in selected_link_timeseries.csv selected_flow_timeseries.csv cbap_packet_trace.csv cbap_tx_events.csv;do [[ ! -f "$dir/$f" ]]||gzip -f "$dir/$f";done;fi
 echo "PASS $id"
}
run_manifest(){ local m="$1" root="$2" victim="${3:-0}" failed=0 id; trap 'jobs -pr|xargs -r kill;wait;exit 130' INT TERM
 while IFS= read -r id;do while (( $(jobs -pr|wc -l)>=MAX_JOBS));do wait -n||failed=1;done;run_one "$m" "$root" "$id" "$victim"& done < <(python3 - "$m" "${SEEDS:-}" <<'PY'
import csv,sys
wanted=set(x.strip() for x in sys.argv[2].split(',') if x.strip())
for row in csv.DictReader(open(sys.argv[1])):
 if not wanted or row['seed'] in wanted: print(row['run_id'])
PY
)
 while (( $(jobs -pr|wc -l) ));do wait -n||failed=1;done;return "$failed"
}
