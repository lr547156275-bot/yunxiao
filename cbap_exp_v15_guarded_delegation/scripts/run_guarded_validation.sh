#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
head -n1 "$ROOT/reports/guarded_semantic_report.md" | grep -qx GUARDED_SEMANTIC_PASS || { echo 'REFUSE: guarded semantic validation has not passed' >&2; exit 2; }
source "$ROOT/scripts/common.sh"
run_manifest "$ROOT/configs/validation_manifest.csv" "$ROOT/runs_validation"
python3 "$ROOT/scripts/analyze_guarded_results.py"
