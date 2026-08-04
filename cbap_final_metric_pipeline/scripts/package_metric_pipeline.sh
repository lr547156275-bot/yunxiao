#!/usr/bin/env bash
set -euo pipefail
PIPE="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="$(cd "$PIPE/.." && pwd)"
grep -q 'METRIC_PIPELINE_PASS' "$PIPE/reports/metric_pipeline_selftest.md"
stamp="$(date +%Y%m%d_%H%M%S)"
archive="$ROOT/cbap_final_metric_pipeline_${stamp}.tar.gz"
list="$(mktemp)"
trap 'rm -f "$list"' EXIT
cd "$ROOT"
find cbap_final_metric_pipeline/scripts cbap_final_metric_pipeline/reports \
  cbap_final_metric_pipeline/processed cbap_final_metric_pipeline/codex_logs \
  cbap_final_metric_pipeline/tests cbap_final_metric_pipeline/preflight \
  -type f -print | sort >"$list"
find cbap_final_metric_pipeline/recomputed -type f \
  \( -name result_full_work.json -o -name flow_outcome_ledger.csv \
     -o -name metric_provenance.json \) -print | sort >>"$list"
sort -u "$list" -o "$list"
grep -v 'cbap_final_metric_pipeline/reports/package_file_hashes.sha256$' "$list" \
  | xargs sha256sum > cbap_final_metric_pipeline/reports/package_file_hashes.sha256
printf '%s\n' cbap_final_metric_pipeline/reports/package_file_hashes.sha256 >>"$list"
sort -u "$list" -o "$list"
tar -czf "$archive" -T "$list"
sha256sum "$archive" >"$archive.sha256"
printf '%s\n%s\n' "$archive" "$archive.sha256"
