#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.."&&pwd)";source "$ROOT/scripts/common.sh";MAX_JOBS="${MAX_JOBS:-1}"
run_manifest "$ROOT/configs/semantic_manifest.csv" "$ROOT/runs_semantic"
python3 "$ROOT/scripts/validate_semantics.py"
