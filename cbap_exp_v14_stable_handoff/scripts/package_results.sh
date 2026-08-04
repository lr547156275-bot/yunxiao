#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$ROOT/cbap_v14_stable_handoff_results_${STAMP}.tar.gz"
cd "$ROOT"
tar -czf "$OUT" \
  cbap_exp_v14_stable_handoff/reports \
  cbap_exp_v14_stable_handoff/processed \
  cbap_exp_v14_stable_handoff/configs \
  cbap_exp_v14_stable_handoff/scripts \
  cbap_exp_v14_stable_handoff/runs_semantic \
  cbap_exp_v14_stable_handoff/runs_validation
sha256sum "$OUT" > "$OUT.sha256"
echo "$OUT"
