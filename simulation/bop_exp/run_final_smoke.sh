#!/usr/bin/env bash
set -euo pipefail
BOP_ROOT="$(cd "$(dirname "$0")" && pwd)"
export RUN_ROOT="${RUN_ROOT:-$BOP_ROOT/final_runs_smoke}"
export BOP_FINAL_VALIDATION=1
source "$BOP_ROOT/scripts/common.sh"

for algorithm in dcqcn dcqcn_wire_equalized bop_qb; do
  bop_run_one gap_50us "$algorithm" 1
done
bop_run_one residual_64k bop_qb 1
bop_run_one residual_64k bop_qb_oracle_q0 1
bop_run_one residual_160k bop_qb_oracle_q0 1
python2 "$BOP_ROOT/scripts/check_final_outputs.py" matrix \
  "$RUN_ROOT" smoke
