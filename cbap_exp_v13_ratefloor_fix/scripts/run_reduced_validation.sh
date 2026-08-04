#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
head -n 1 "$ROOT/reports/ratefloor_semantic_report.md" | grep -qx 'RATEFLOOR_SEMANTIC_PASS' || {
  echo 'REFUSE: rate-floor semantic validation has not passed' >&2; exit 2;
}
source "$ROOT/scripts/common.sh"
run_manifest "$ROOT/configs/reduced_manifest.csv" "$ROOT/runs_reduced"
python3 "$ROOT/scripts/analyze_reduced_results.py"
