#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/scripts/common.sh"
clos_run_manifest "${SEEDS:-1,2,3}" all

