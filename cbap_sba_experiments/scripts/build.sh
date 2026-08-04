#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TEST_BUILD="$ROOT/cbap_sba_experiments/tests/.build"
mkdir -p "$TEST_BUILD"

g++ -std=c++11 -Wall -Wextra -Werror -pedantic \
  -I"$ROOT/simulation/src/point-to-point/model" \
  "$ROOT/simulation/src/point-to-point/model/cbap-sba.cc" \
  "$ROOT/cbap_sba_experiments/tests/cbap_sba_reduced_test.cc" \
  -o "$TEST_BUILD/cbap_sba_reduced_test"

cd "$ROOT/simulation"
python2 ./waf build
