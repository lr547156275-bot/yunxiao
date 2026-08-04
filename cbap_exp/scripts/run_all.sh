#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/common.sh"
RUN_ROOT="${RUN_ROOT:-$ROOT/runs}"
run_manifest
python3 "$ROOT/scripts/analyze_results.py" --runs "$RUN_ROOT"
