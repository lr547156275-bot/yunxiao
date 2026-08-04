#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.."&&pwd)";report="$ROOT/reports/semantic_regression_report.md"
[[ -f "$report" && "$(head -1 "$report")" == SEMANTIC_PASS ]]||{ echo 'REFUSE: semantic regression is not SEMANTIC_PASS' >&2;exit 1;}
source "$ROOT/scripts/common.sh";MAX_JOBS="${MAX_JOBS:-4}"
run_manifest "$ROOT/configs/freeze_manifest.csv" "$ROOT/runs_formal"
echo FREEZE_VALIDATION_RUNS_COMPLETE_NO_CONCLUSION
