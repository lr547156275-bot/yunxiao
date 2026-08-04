#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/scripts/common.sh"
clos_run_ids \
  clos_1to1_64h__all_to_all__32__1MiB__dctcp__seed1 \
  clos_1to1_64h__all_to_all__32__1MiB__dcqcn__seed1 \
  clos_1to1_64h__all_to_all__32__1MiB__timely__seed1 \
  clos_1to1_64h__all_to_all__32__1MiB__hpcc_int__seed1 \
  clos_1to1_64h__all_to_all__32__1MiB__bop_qb__seed1 \
  clos_1to1_64h__ring_allreduce_1d__64__1MiB__dcqcn__seed1 \
  clos_1to1_64h__ring_allreduce_1d__64__1MiB__hpcc_int__seed1 \
  clos_1to1_64h__ring_allreduce_1d__64__1MiB__bop_qb__seed1 \
  clos_1to1_64h__hierarchical_allreduce_2d__64__64MiB__dcqcn__seed1 \
  clos_1to1_64h__hierarchical_allreduce_2d__64__64MiB__bop_qb__seed1

