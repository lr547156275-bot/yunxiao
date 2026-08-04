#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SEEDS="${SEEDS:-1,2,3}"
source "$ROOT/scripts/common.sh"
main_run_rows "main,ablation,wire_fairness" "$SEEDS"
python3 "$ROOT/scripts/check_main_outputs.py" matrix "$RUN_ROOT" --seeds "$SEEDS"
python3 "$ROOT/scripts/parse_main_results.py" --runs "$RUN_ROOT"
