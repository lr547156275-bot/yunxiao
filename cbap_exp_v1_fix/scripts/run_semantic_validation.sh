#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/common.sh"
export MAX_JOBS="${MAX_JOBS:-1}"
run_manifest "$ROOT/config/semantic_manifest.csv" "$ROOT/runs_semantic"
python3 "$ROOT/scripts/validate_semantics.py" --runs "$ROOT/runs_semantic"
