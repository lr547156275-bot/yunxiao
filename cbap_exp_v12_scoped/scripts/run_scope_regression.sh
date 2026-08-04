#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.."&&pwd)";source "$ROOT/scripts/common.sh"
run_manifest "$ROOT/configs/scope_manifest.csv" "$ROOT/runs_scope"
python3 "$ROOT/scripts/analyze_scope_regression.py"
