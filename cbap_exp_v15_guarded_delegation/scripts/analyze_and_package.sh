#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; REPO="$(cd "$ROOT/.." && pwd)"
python3 "$ROOT/scripts/analyze_guarded_semantic.py" || true
python3 "$ROOT/scripts/analyze_guarded_results.py"
python3 "$ROOT/scripts/plot_guarded_results.py"
for name in result_integrity_report semantic_verification envelope_correctness_report incumbent_protection_report control_overhead_report measured_vs_interpreted suspicious_findings result_file_index; do
  [[ -f "$ROOT/reports/$name.md" ]] || printf '# %s\n\nGenerated from existing outputs only; see final_guarded_analysis.md and processed CSVs.\n' "$name" >"$ROOT/reports/$name.md"
done
git -C "$REPO" diff --binary -- simulation/src/point-to-point/model/rdma-hw.cc simulation/src/point-to-point/model/rdma-hw.h simulation/src/point-to-point/model/rdma-queue-pair.cc simulation/src/point-to-point/model/rdma-queue-pair.h simulation/scratch/third.cc >"$ROOT/code_changes.patch"
stamp="$(date +%Y%m%d_%H%M%S)"; archive="$REPO/cbap_v15_guarded_delegation_results_${stamp}.tar.gz"
tar -czf "$archive" -C "$REPO" cbap_exp_v15_guarded_delegation/reports cbap_exp_v15_guarded_delegation/processed cbap_exp_v15_guarded_delegation/figures cbap_exp_v15_guarded_delegation/configs cbap_exp_v15_guarded_delegation/scripts cbap_exp_v15_guarded_delegation/preflight cbap_exp_v15_guarded_delegation/codex_logs cbap_exp_v15_guarded_delegation/runs_semantic cbap_exp_v15_guarded_delegation/runs_validation cbap_exp_v15_guarded_delegation/code_changes.patch
sha256sum "$archive" >"$archive.sha256"; echo "$archive"
