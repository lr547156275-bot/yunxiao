#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.."&&pwd)";OUT="$ROOT/cbap_exp_v11_freeze/reports";mkdir -p "$OUT";export NS_LOG="";ulimit -c 0
{ date -Is;python2 --version;python3 --version;g++ --version|head -1;echo 'command: python2 ./waf build';cd "$ROOT/simulation";python2 ./waf build;} >"$OUT/build_full.log" 2>&1
printf '# CBAP-v1.1 build report\n\n- Status: PASS\n- Command: `python2 ./waf build`\n- Full log: `cbap_exp_v11_freeze/reports/build_full.log`\n- ns-3 experiments: 0\n' >"$OUT/build_report.md";echo BUILD_PASS
