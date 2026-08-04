#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
source "$ROOT/scripts/common.sh"
SEEDS=1
main_run_explicit \
  msg_64k_n16_g50:pfc_only:1 \
  msg_64k_n16_g50:dctcp:1 \
  msg_64k_n16_g50:dcqcn:1 \
  msg_64k_n16_g50:timely:1 \
  msg_64k_n16_g50:hpcc_int:1 \
  msg_64k_n16_g50:bop_qb:1 \
  msg_64k_n16_g50:crfm_gate:1 \
  msg_64k_n16_g50:bop:1 \
  msg_64k_n16_g50:dcqcn_wire_equalized:1
