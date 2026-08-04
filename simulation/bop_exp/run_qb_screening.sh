#!/usr/bin/env bash
set -euo pipefail
BOP_ROOT="$(cd "$(dirname "$0")" && pwd)"
export RUN_ROOT="${RUN_ROOT:-$BOP_ROOT/qb_runs}"
source "$BOP_ROOT/scripts/common.sh"
CASES_DEFAULT="gap_20us,gap_50us,single_round,n32_64k,size_256k,heterogeneous,long_burst"
bop_matrix "${CASES:-$CASES_DEFAULT}" \
  "${ALGOS:-dcqcn,crfm_gate,bop,bop_qc,bop_qb}" "${SEEDS:-1}"
python2 "$BOP_ROOT/scripts/check_qb_outputs.py" matrix "$RUN_ROOT"
