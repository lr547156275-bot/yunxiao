#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SEEDS="${SEEDS:-1,2,3}"
source "$ROOT/scripts/common.sh"
main_run_rows "main,ablation,wire_fairness" "$SEEDS"
