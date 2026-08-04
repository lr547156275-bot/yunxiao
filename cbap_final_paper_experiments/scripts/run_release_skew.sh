#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"
run_manifest_final "$FINAL_ROOT/manifests/release_skew.csv" "$FINAL_ROOT/runs_release_skew"
