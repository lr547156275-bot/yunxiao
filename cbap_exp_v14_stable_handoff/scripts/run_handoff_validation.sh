#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
head -n 1 "$ROOT/reports/handoff_semantic_report.md" | \
  grep -qx 'HANDOFF_SEMANTIC_PASS' || {
    echo 'REFUSE: stable-handoff semantic validation has not passed' >&2
    exit 2
  }
source "$ROOT/scripts/common.sh"
run_manifest "$ROOT/configs/validation_manifest.csv" "$ROOT/runs_validation"
python3 "$ROOT/scripts/analyze_handoff_results.py"
