#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPORT="$ROOT/reports/semantic_validation_report.md"
if [[ ! -f "$REPORT" ]] || [[ "$(head -n 1 "$REPORT")" != "SEMANTIC_PASS" ]]; then
  echo "REFUSE formal run: semantic validation is not SEMANTIC_PASS" >&2
  exit 1
fi
source "$ROOT/scripts/common.sh"
export MAX_JOBS="${MAX_JOBS:-4}"
run_manifest "$ROOT/config/formal_manifest.csv" "$ROOT/runs_formal"
echo "FORMAL_REDUCED_COMPLETE_NO_RESEARCH_CONCLUSION"
