#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
"$ROOT/cbap_sba_experiments/scripts/build.sh"
python3 "$ROOT/cbap_sba_experiments/scripts/validate_semantics.py"
CBAP_SBA_SKIP_BUILD=1 "$ROOT/cbap_sba_experiments/scripts/run_smoke.sh"
