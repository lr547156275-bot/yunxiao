#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$(dirname "$ROOT")/cbap_v13_ratefloor_fix_results_${STAMP}.tar.gz"
tar -czf "$OUT" -C "$(dirname "$ROOT")" \
  cbap_exp_v13_ratefloor_fix/reports cbap_exp_v13_ratefloor_fix/processed \
  cbap_exp_v13_ratefloor_fix/configs cbap_exp_v13_ratefloor_fix/scripts \
  cbap_exp_v13_ratefloor_fix/runs_semantic cbap_exp_v13_ratefloor_fix/runs_reduced
sha256sum "$OUT" > "$OUT.sha256"
echo "$OUT"
