#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/cbap_exp_v15_guarded_delegation/reports/build.log"
cd "$ROOT/simulation"
python2 ./waf build >"$OUT" 2>&1
echo "BUILD_PASS log=$OUT"
