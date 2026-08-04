#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$(dirname "$ROOT")"
stamp="$(date +%Y%m%d_%H%M%S)"
archive="cbap_final_paper_results_${stamp}.tar.gz"
tar -czf "$archive" \
  cbap_final_paper_experiments/manifests \
  cbap_final_paper_experiments/processed \
  cbap_final_paper_experiments/figures \
  cbap_final_paper_experiments/reports
sha256sum "$archive" >"$archive.sha256"
printf '%s\n' "$archive"
