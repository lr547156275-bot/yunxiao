#!/bin/bash
# Adapt the matrix tooling to a local checkout.
#
# The scripts were written against a container that mounted the ns-3 tree at
# /work/simulation with logs in /work/matrix_logs.  On a normal machine both
# paths differ, so this rewrites them once, in place, from wherever the repo
# actually sits.
#
# Usage:
#   cd <repo>/simulation/experiment/scheme1_sba
#   bash setup_local.sh [logs_dir]
#
# Default logs_dir is $HOME/matrix_logs.  Idempotent: running it twice is safe.
set -u

HERE=$(cd "$(dirname "$0")" && pwd)
SIM=$(cd "$HERE/../.." && pwd)          # .../simulation
LOGS=${1:-$HOME/matrix_logs}

echo "repo simulation dir : $SIM"
echo "logs dir            : $LOGS"
mkdir -p "$LOGS"

# Shell scripts: SIM= and LOGS= assignments near the top.
for f in run_matrix.sh run_all.sh status.sh; do
  [ -f "$HERE/$f" ] || { echo "  missing $f"; continue; }
  sed -i "s|^SIM=/work/simulation$|SIM=$SIM|" "$HERE/$f"
  sed -i "s|^LOGS=/work/matrix_logs$|LOGS=$LOGS|" "$HERE/$f"
  # status.sh has no SIM but does reference the script path
  sed -i "s|/work/simulation/experiment/scheme1_sba|$HERE|g" "$HERE/$f"
  echo "  patched $f"
done

# Python tools: module-level LOGS constants.
sed -i "s|^LOGS = '/work/matrix_logs'|LOGS = '$LOGS'|" "$HERE/metrics.py"
sed -i "s|^LOGS = '/work/matrix_logs'|LOGS = '$LOGS'|" "$HERE/build_report.py"
sed -i "s|    logs = '/work/matrix_logs'|    logs = '$LOGS'|" "$HERE/verify_triggers.py"
sed -i "s|    logdir = '/work/matrix_logs'|    logdir = '$LOGS'|" "$HERE/metrics.py"
echo "  patched metrics.py verify_triggers.py build_report.py"

echo ""
echo "=== remaining /work references (should be none) ==="
grep -n "/work/" "$HERE"/run_matrix.sh "$HERE"/run_all.sh "$HERE"/status.sh \
    "$HERE"/metrics.py "$HERE"/verify_triggers.py "$HERE"/build_report.py \
    2>/dev/null | grep -v "^.*#" | head -10 || echo "  none"

echo ""
echo "=== syntax check ==="
for f in run_matrix.sh run_all.sh status.sh; do
  bash -n "$HERE/$f" && echo "  $f OK" || echo "  $f SYNTAX ERROR"
done
for f in metrics.py verify_triggers.py build_report.py; do
  python2 -m py_compile "$HERE/$f" 2>/dev/null && echo "  $f OK" \
    || echo "  $f SYNTAX ERROR (needs python2)"
done

cat <<EOF

=== next steps ===

1. Build (waf requires python2; gcc-5 or gcc-7 both work):
     cd $SIM
     CC=gcc-5 CXX=g++-5 python2 waf configure
     CC=gcc-5 CXX=g++-5 python2 waf build

2. Run the matrix (serial, resumable, ~11.5 h for all 30 cells):
     cd $SIM
     bash experiment/scheme1_sba/run_all.sh

   Re-run the same command after any interruption; completed cells are skipped.

3. Watch progress:
     bash experiment/scheme1_sba/status.sh

4. Assemble deliverables once cells are done:
     cd experiment/scheme1_sba
     python2 build_report.py 2

Notes
  * Seed is 2, not 1.  third.cc:3441 reserves SIM_SEED 1 for diagnostics and
    demands a bounded CBAP packet trace that the scenario configs do not set,
    so seed 1 fails every cell with CONFIG_ERROR.
  * The simulation consumes no random variates on any reachable path, so
    results are deterministic.  Sanity check: S1 / DCQCN should give a mean
    incast FCT of 17.399 ms.  A different number means the environment differs.
  * MAX_JOBS=1 is enforced.  Two concurrent ns-3 runs on two cores measured
    15-20x slower per cell than serial; only try parallel with many cores.
EOF
