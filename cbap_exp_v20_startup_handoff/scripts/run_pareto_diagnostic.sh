#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/common.sh"
run_manifest "$ROOT/configs/pareto_manifest.csv" "$ROOT/runs_pareto"
python3 "$ROOT/scripts/analyze_pareto.py"
