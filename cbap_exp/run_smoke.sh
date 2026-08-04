#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
export RUN_ROOT="${RUN_ROOT:-$ROOT/runs_smoke}"
export MAX_JOBS="${MAX_JOBS:-1}"
source "$ROOT/scripts/common.sh"
run_ids \
  e1_single_old_single_new__default__dcqcn__seed1 \
  e1_single_old_single_new__default__hpcc_int__seed1 \
  e1_single_old_single_new__default__bop_qb__seed1 \
  e1_single_old_single_new__default__cbap_full__seed1
