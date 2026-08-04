#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
for script in run_single_bottleneck.sh run_release_skew.sh \
              run_multibottleneck.sh run_clos.sh \
              run_randomized_robustness.sh run_ablations.sh; do
  "$HERE/$script"
done
