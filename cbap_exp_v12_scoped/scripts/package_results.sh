#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.."&&pwd)";STAMP="$(date +%Y%m%d_%H%M%S)"
cd "$(dirname "$ROOT")";tar -czf "cbap_v12_scoped_results_${STAMP}.tar.gz" cbap_exp_v12_scoped/{reports,processed,configs,scripts,preflight,runs_scope,runs_core}
echo "cbap_v12_scoped_results_${STAMP}.tar.gz"
