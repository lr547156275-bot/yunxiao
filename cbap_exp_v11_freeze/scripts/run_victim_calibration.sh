#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.."&&pwd)";source "$ROOT/scripts/common.sh";MAX_JOBS="${MAX_JOBS:-1}"
run_manifest "$ROOT/configs/victim_manifest.csv" "$ROOT/victim_calibration" 1
python3 "$ROOT/scripts/analyze_victim_calibration.py"
