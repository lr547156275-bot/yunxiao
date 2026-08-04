#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CONFIG="$ROOT/cbap_sba_experiments/configs/smoke"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="$ROOT/cbap_sba_experiments/runs/smoke_$STAMP"

if [[ "${CBAP_SBA_SKIP_BUILD:-0}" != "1" ]]; then
  "$ROOT/cbap_sba_experiments/scripts/build.sh"
fi
mkdir -p "$RUN_DIR"
cp "$CONFIG"/* "$RUN_DIR"/
printf '%s\n' "python2 ./waf --cwd=$RUN_DIR --run scratch/third\ $RUN_DIR/config.txt" \
  >"$RUN_DIR/command.txt"
cd "$ROOT/simulation"
timeout 180s python2 ./waf --cwd="$RUN_DIR" \
  --run "scratch/third $RUN_DIR/config.txt" >"$RUN_DIR/run.log" 2>&1
python3 "$ROOT/cbap_sba_experiments/scripts/validate_semantics.py" \
  --smoke-dir "$RUN_DIR"
printf 'SMOKE_RUN_DIR=%s\n' "$RUN_DIR"
