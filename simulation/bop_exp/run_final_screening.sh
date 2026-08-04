#!/usr/bin/env bash
set -euo pipefail
BOP_ROOT="$(cd "$(dirname "$0")" && pwd)"
export RUN_ROOT="${RUN_ROOT:-$BOP_ROOT/final_runs}"
export BOP_FINAL_VALIDATION=1
source "$BOP_ROOT/scripts/common.sh"

seeds="${SEEDS:-1}"
bop_matrix "gap_20us,gap_50us,single_round,n32_64k" \
  "dcqcn,dcqcn_wire_equalized,bop_qb" "$seeds"
bop_matrix "residual_64k,residual_160k" \
  "dcqcn,crfm_gate,bop_qb,bop_qb_oracle_q0" "$seeds"
python2 "$BOP_ROOT/scripts/check_final_outputs.py" matrix \
  "$RUN_ROOT" screening
