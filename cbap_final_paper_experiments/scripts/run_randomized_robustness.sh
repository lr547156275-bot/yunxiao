#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"
run_manifest_final "$FINAL_ROOT/manifests/randomized_robustness.csv" "$FINAL_ROOT/runs_randomized"
