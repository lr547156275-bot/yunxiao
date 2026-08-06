#!/bin/bash
# Multi-algorithm comparison matrix runner.
#
# Usage:  bash run_matrix.sh <scenario_tag> <stop_time> <seeds...>
#   e.g.  bash run_matrix.sh s1 3.0 2 3 4 5 6
#         bash run_matrix.sh s3 4.0 2
#
# All algorithms share one scenario, one stop time and one seed list, so the
# only configuration differences are CC_MODE / CBAP_ENABLE / ALGORITHM.
#
# Resumable and safe to re-invoke:
#   * a cell is "done" only when the expected number of incast flows all
#     completed -- exit 0 with a truncated flow_summary.csv does NOT count;
#   * each cell writes a manifest recording algorithm, seed, config hash and
#     output path;
#   * nothing is ever deleted, and no wildcard removal is performed.
set -u

TAG=${1:?usage: run_matrix.sh <tag> <stop_time> <seeds...>}
STOP=${2:?usage: run_matrix.sh <tag> <stop_time> <seeds...>}
shift 2
SEEDS="$*"
[ -n "$SEEDS" ] || { echo "no seeds given"; exit 1; }

SIM=/work/simulation
D=experiment/scheme1_sba
LOGS=/work/matrix_logs
cd "$SIM"
mkdir -p "$LOGS"

BASECFG=$D/${TAG}_config.txt
[ -f "$BASECFG" ] || { echo "missing $BASECFG"; exit 1; }
FLOWFILE=$D/$(awk '/^FLOW_FILE/{print $2}' "$BASECFG")
[ -f "$FLOWFILE" ] || { echo "missing flow file $FLOWFILE"; exit 1; }

# Background sources: S6 has two (one per bottleneck), the others one.
if [ "$TAG" = "s6" ]; then BG_RE='^(65|61)$'; else BG_RE='^65$'; fi
EXPECTED=$(awk -v re="$BG_RE" 'NR>1 && $1 !~ re {n++} END{print n+0}' "$FLOWFILE")
STOPNS=$(python2 -c "print int(float('$STOP')*1e9)")

echo "matrix: tag=$TAG stop=${STOP}s seeds=[$SEEDS] expected_incast=$EXPECTED"
echo ""

# algo -> CC_MODE / CBAP_ENABLE / migration
cc_of()   { case $1 in dcqcn) echo 1;; hpcc) echo 3;; timely) echo 7;;
                       dctcp) echo 8;; cbapsba) echo 30;; esac; }
cbap_of() { case $1 in cbapsba) echo 1;; *) echo 0;; esac; }
mig_of()  { case $1 in cbapsba) echo 1;; *) echo 0;; esac; }

build_cfg() {
  local algo=$1 seed=$2 out=$3 cfg=$4
  awk -v cc="$(cc_of $algo)" -v cbap="$(cbap_of $algo)" -v seed="$seed" \
      -v algo="$algo" -v stop="$STOP" -v stopns="$STOPNS" -v out="$out" \
      -v tag="$TAG" '
    NF==0 { next }
    $1=="CC_MODE"                    { print "CC_MODE " cc; next }
    $1=="CBAP_ENABLE"                { print "CBAP_ENABLE " cbap; next }
    $1=="SIM_SEED"                   { print "SIM_SEED " seed; next }
    $1=="ALGORITHM"                  { print "ALGORITHM " algo; next }
    $1=="SIMULATOR_STOP_TIME"        { print "SIMULATOR_STOP_TIME " stop; next }
    $1=="QLEN_MON_END"               { print "QLEN_MON_END " stopns; next }
    # Flow 0 is the background flow; it must occupy a rate-trace slot so its
    # throughput, minimum and recovery time are measurable.
    $1=="ROUND_TRACE_SELECTED_FLOWS" { print "ROUND_TRACE_SELECTED_FLOWS 0,1,2,3"; next }
    $1=="CBAP_MIGRATION_ENABLE"      { next }
    $1=="CBAP_MIGRATION_TRACE"       { next }
    $1=="APP_CAP_TRACE"              { next }
    { gsub(tag "_out/", out "/"); print }
  ' "$BASECFG" > "$cfg"
  if [ "$(mig_of $algo)" = "1" ]; then
    echo "CBAP_MIGRATION_ENABLE 1" >> "$cfg"
    echo "CBAP_MIGRATION_TRACE 0" >> "$cfg"
  fi
}

completed_incast() {
  local f=$1
  [ -s "$f" ] || { echo 0; return; }
  # column 6 = src, 13 = completed
  awk -F, -v re="$BG_RE" 'NR>1 && $6 !~ re && $13==1 {n++} END{print n+0}' "$f"
}

run_cell() {
  local algo=$1 seed=$2
  local name="m_${algo}_${TAG}_seed${seed}"
  local out="${name}_out"
  local cfg="$D/${name}.txt"
  local flag="$LOGS/${name}.done"
  if [ -f "$flag" ]; then echo "SKIP $name"; return 0; fi

  mkdir -p "$D/$out"
  build_cfg "$algo" "$seed" "$out" "$cfg"
  python2 waf --cwd=$D --run "scratch/third ${name}.txt" \
      > "$LOGS/${name}.log" 2>&1
  local code=$?
  local got
  got=$(completed_incast "$D/$out/flow_summary.csv")

  # Per-cell manifest, written whatever the outcome.
  {
    echo "algorithm=$algo"
    echo "cc_mode=$(cc_of $algo)"
    echo "cbap_enable=$(cbap_of $algo)"
    echo "migration=$(mig_of $algo)"
    echo "scenario=$TAG"
    echo "seed=$seed"
    echo "stop_time=$STOP"
    echo "expected_incast=$EXPECTED"
    echo "completed_incast=$got"
    echo "exit_code=$code"
    echo "config=$cfg"
    echo "config_sha256=$(sha256sum "$cfg" | cut -d' ' -f1)"
    echo "output_dir=$D/$out"
    echo "log=$LOGS/${name}.log"
  } > "$LOGS/${name}.manifest"

  if [ "$code" -eq 0 ] && [ "$got" -eq "$EXPECTED" ]; then
    touch "$flag"
    echo "OK   $name ($got/$EXPECTED incast)"
  else
    echo "FAIL $name (exit=$code, $got/$EXPECTED incast)"
    grep -E "CONFIG_ERROR|assert|terminate" "$LOGS/${name}.log" | head -1
  fi
}

# Two cores: run algorithms in pairs within each seed.
for seed in $SEEDS; do
  run_cell dcqcn  "$seed" & run_cell hpcc   "$seed" & wait
  run_cell timely "$seed" & run_cell dctcp  "$seed" & wait
  run_cell cbapsba "$seed" & wait
  echo "===== seed $seed complete ($(ls "$LOGS"/m_*_${TAG}_*.done 2>/dev/null | wc -l) cells done) ====="
done

TOTAL=$(ls "$LOGS"/m_*_${TAG}_*.done 2>/dev/null | wc -l)
echo ""
echo "===== MATRIX $TAG COMPLETE: $TOTAL cells done ====="
echo "extract with: python2 $D/metrics.py $TAG"
