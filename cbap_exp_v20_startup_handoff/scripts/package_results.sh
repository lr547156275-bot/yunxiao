#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$REPO/cbap_v20_startup_handoff_results_${STAMP}.tar.gz"
cd "$REPO"
tar -czf "$OUT" \
  cbap_exp_v20_startup_handoff/reports \
  cbap_exp_v20_startup_handoff/processed \
  cbap_exp_v20_startup_handoff/figures \
  cbap_exp_v20_startup_handoff/configs \
  cbap_exp_v20_startup_handoff/scripts \
  cbap_exp_v20_startup_handoff/runs_semantic \
  cbap_exp_v20_startup_handoff/runs_pareto
sha256sum "$OUT" > "$OUT.sha256"
echo "$OUT"
