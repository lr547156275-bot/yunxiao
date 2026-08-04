#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/cbap_exp_v1_fix/reports"
mkdir -p "$OUT"
export NS_LOG=""
ulimit -c 0
{
  date -Is
  python2 --version
  python3 --version
  g++ --version | head -n 1
  echo "command: python2 ./waf build"
  cd "$ROOT/simulation"
  python2 ./waf build
} >"$OUT/build_full.log" 2>&1
cat >"$OUT/build_report.md" <<REPORT
# CBAP-v1 build report

- Status: PASS
- Command: \`python2 ./waf build\`
- Python 2: \`$(python2 --version 2>&1)\`
- Python 3: \`$(python3 --version 2>&1)\`
- Compiler: \`$(g++ --version | head -n 1)\`
- Full log: \`cbap_exp_v1_fix/reports/build_full.log\`
- ns-3 experiments executed by this script: 0
REPORT
echo "BUILD_PASS"
