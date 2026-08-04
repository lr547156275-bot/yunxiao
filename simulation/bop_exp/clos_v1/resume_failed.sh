#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/scripts/common.sh"
clos_require_regression
mapfile -t pending < <(python3 "$CLOS_ROOT/scripts/check_clos_outputs.py" \
  --list-invalid "$RUN_ROOT" --seeds "${SEEDS:-1,2,3}")
(( ${#pending[@]} )) || { echo "No missing or invalid runs."; exit 0; }
clos_run_ids "${pending[@]}"
