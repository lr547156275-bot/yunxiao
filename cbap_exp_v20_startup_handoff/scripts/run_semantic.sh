#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/common.sh"
run_manifest "$ROOT/configs/semantic_manifest.csv" "$ROOT/runs_semantic"
python3 "$ROOT/scripts/analyze_semantic.py"
