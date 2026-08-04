#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.."&&pwd)"
head -n 1 "$ROOT/reports/scope_regression_report.md" |
  grep -qx 'SCOPE_REGRESSION_PASS'||{
    echo 'REFUSE: scope regression has not passed' >&2
    exit 2
  }
source "$ROOT/scripts/common.sh"
run_manifest "$ROOT/configs/core_manifest.csv" "$ROOT/runs_core"
python3 "$ROOT/scripts/analyze_core_results.py"
