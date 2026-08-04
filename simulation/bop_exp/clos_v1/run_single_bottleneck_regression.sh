#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SIM="$(cd "$ROOT/../.." && pwd)"
OUT="$ROOT/single_bottleneck_regression"
MIN_FREE_GB="${MIN_FREE_GB:-5}"
RUN_TIMEOUT_MIN="${RUN_TIMEOUT_MIN:-60}"
export NS_LOG=""
ulimit -c 0
mkdir -p "$OUT"
rm -f "$OUT/PASS.flag"
free_kb="$(df -Pk "$OUT" | awk 'NR==2 {print $4}')"
required_kb="$(awk -v v="$MIN_FREE_GB" 'BEGIN {printf "%.0f",v*1024*1024}')"
(( free_kb >= required_kb )) || {
  echo "REFUSE less than ${MIN_FREE_GB} GiB free" >&2; exit 1; }
for scenario in msg_64k_n16_g50 msg_256k_n16_g50 n32_64k_g50; do
  run_dir="$(python3 "$ROOT/scripts/regression.py" prepare "$scenario")"
  rm -f "$run_dir"/{flow_summary.csv,round_summary.csv,feedback_summary.csv,controller_summary.csv,group_round_summary.csv,flow_plan.csv,selected_link_timeseries.csv,selected_flow_timeseries.csv,pfc_events.csv,bop_qb_group_decisions.csv}
  (
    cd "$SIM"
    timeout --signal=TERM --kill-after=30s "${RUN_TIMEOUT_MIN}m" \
      python2 ./waf --cwd="$run_dir" \
        --run "scratch/third $run_dir/config.txt"
  ) 2>&1 | tail -c 10485760 >"$run_dir/run.log"
  python3 "$ROOT/scripts/regression.py" check "$scenario"
done
printf 'SINGLE_BOTTLENECK_REGRESSION_PASS\n' >"$OUT/PASS.flag"
echo "PASS all three single-bottleneck regressions; Clos gate opened"
