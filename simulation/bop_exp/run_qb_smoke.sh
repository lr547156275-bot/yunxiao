#!/usr/bin/env bash
set -euo pipefail
BOP_ROOT="$(cd "$(dirname "$0")" && pwd)"
export RUN_ROOT="${RUN_ROOT:-$BOP_ROOT/qb_runs_smoke}"
source "$BOP_ROOT/scripts/common.sh"
bop_seed_preflight gap_20us
for algorithm in dcqcn crfm_gate bop bop_qc bop_qb; do
  bop_run_one gap_20us "$algorithm" 1
done
bop_run_one n32_64k bop_qb 1
bop_run_one heterogeneous bop_qb 1
bop_run_one long_burst bop_qb 1
python2 "$BOP_ROOT/scripts/check_qb_outputs.py" matrix "$RUN_ROOT"
