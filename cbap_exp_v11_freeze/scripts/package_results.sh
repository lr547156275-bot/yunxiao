#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.."&&pwd)";cd "$ROOT";stamp="$(date +%Y%m%d_%H%M%S)";archive="cbap_v11_freeze_results_${stamp}.tar.gz"
tar -czf "$archive" cbap_exp_v11_freeze/reports cbap_exp_v11_freeze/processed cbap_exp_v11_freeze/configs cbap_exp_v11_freeze/scripts cbap_exp_v11_freeze/preflight cbap_exp_v11_freeze/codex_logs ${INCLUDE_RUNS:+cbap_exp_v11_freeze/runs_semantic cbap_exp_v11_freeze/runs_formal}
sha256sum "$archive">"$archive.sha256";echo "$ROOT/$archive"
