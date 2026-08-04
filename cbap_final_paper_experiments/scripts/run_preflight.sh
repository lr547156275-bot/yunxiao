#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"
run_manifest_final "$FINAL_ROOT/manifests/preflight.csv" "$FINAL_ROOT/preflight/runs"
python3 "$FINAL_ROOT/scripts/audit_framework.py" --preflight-results
