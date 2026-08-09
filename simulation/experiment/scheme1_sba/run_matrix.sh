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
# Trace-completeness bounds: the link trace must reach the end of the monitored
# window.  QLEN_MON_END is forced to the stop time by build_cfg below, so the
# expected end is the stop time itself.
QLEN_END_S=$STOP
SAMPLE_S=$(awk '/^CRFM_TRACE_SAMPLE_US/{printf "%.9f", $2/1e6; exit}' "$BASECFG")
[ -n "$SAMPLE_S" ] || SAMPLE_S=0.00001

# Hash gate: refuse to run if the topology, the binary or the commit moved since
# the baseline was taken, so a mid-matrix rebuild cannot silently mix results.
BASE_MF=$LOGS/matrix_baseline.manifest
if [ -f "$BASE_MF" ]; then
  want_topo=$(awk -F= '$1=="topology_sha256"{print $2}' "$BASE_MF")
  want_bin=$(awk -F= '$1=="binary_sha256"{print $2}' "$BASE_MF")
  have_topo=$(sha256sum "$D/topology.txt" | cut -d' ' -f1)
  have_bin=$(sha256sum build/scratch/third | cut -d' ' -f1)
  if [ -n "$want_topo" ] && [ "$want_topo" != "$have_topo" ]; then
    echo "HASH MISMATCH: topology.txt changed since the baseline"; exit 1
  fi
  if [ -n "$want_bin" ] && [ "$want_bin" != "$have_bin" ]; then
    echo "HASH MISMATCH: build/scratch/third changed since the baseline"
    echo "  baseline=$want_bin"
    echo "  current =$have_bin"
    exit 1
  fi
fi

echo "matrix: tag=$TAG stop=${STOP}s seeds=[$SEEDS] expected_incast=$EXPECTED"
echo "        serial (MAX_JOBS=1), trace must reach ${QLEN_END_S}s"
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

# A trace that hit CRFM_MAX_TRACE_FILE_MB or ran out of disk stops early but
# still exits 0.  Queue percentiles from a truncated trace look plausible and
# are wrong, so completeness is part of the done criterion, not an afterthought.
trace_complete() {
  local f=$1 log=$2
  [ -s "$f" ] || { echo "missing"; return; }
  if grep -q "LOG_TRUNCATED" "$log" 2>/dev/null; then echo "truncated"; return; fi
  local last
  last=$(awk -F, 'NF>=9 {t=$1} END{printf "%.6f", t+0}' "$f")
  # Must reach within two sample intervals of the monitored window's end.
  local ok
  ok=$(awk -v l="$last" -v e="$QLEN_END_S" -v s="$SAMPLE_S" \
      'BEGIN{print (l >= e - 2*s) ? "ok" : "short"}')
  if [ "$ok" = "ok" ]; then echo "ok"; else echo "short:${last}/${QLEN_END_S}"; fi
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
  local t0 t1
  t0=$(date +%s)
  # timeout so a genuinely hung cell fails as an anomaly instead of stalling
  # the whole matrix; --kill-after because waf may not pass the signal on.
  timeout --kill-after=60 "${CELL_TIMEOUT:-10800}" \
      python2 waf --cwd=$D --run "scratch/third ${name}.txt" \
      > "$LOGS/${name}.log" 2>&1
  local code=$?
  t1=$(date +%s)
  local got trace
  got=$(completed_incast "$D/$out/flow_summary.csv")
  trace=$(trace_complete "$D/$out/selected_link_timeseries.csv" "$LOGS/${name}.log")

  # Per-cell manifest, written whatever the outcome.  Everything here is read
  # back from the generated config, so it describes what actually ran.
  local g=$D/${name}.txt
  cfgval() { awk -v k="$1" '$1==k{$1=""; sub(/^ /,""); print; exit}' "$g"; }
  {
    echo "algorithm=$algo"
    echo "cc_mode=$(cc_of $algo)"
    echo "cbap_enable=$(cbap_of $algo)"
    echo "migration=$(mig_of $algo)"
    echo "scenario=$TAG"
    echo "scenario_name=$(cfgval SCENARIO)"
    echo "seed=$seed"
    echo "stop_time=$STOP"
    echo "qlen_mon_start=$(cfgval QLEN_MON_START)"
    echo "qlen_mon_end=$(cfgval QLEN_MON_END)"
    echo "kmin_map=$(cfgval KMIN_MAP)"
    echo "kmax_map=$(cfgval KMAX_MAP)"
    echo "pmax_map=$(cfgval PMAX_MAP)"
    echo "pause_time=$(cfgval PAUSE_TIME)"
    echo "buffer_size=$(cfgval BUFFER_SIZE)"
    echo "enable_qcn=$(cfgval ENABLE_QCN)"
    echo "dynamic_pfc_threshold=$(cfgval USE_DYNAMIC_PFC_THRESHOLD)"
    echo "app_rate_cap_flow=$(cfgval APP_RATE_CAP_FLOW)"
    echo "app_rate_cap_bps=$(cfgval APP_RATE_CAP_BPS)"
    echo "selected_links=$(cfgval ROUND_TRACE_SELECTED_LINKS)"
    echo "selected_flows=$(cfgval ROUND_TRACE_SELECTED_FLOWS)"
    echo "sample_us=$(cfgval CRFM_TRACE_SAMPLE_US)"
    echo "expected_incast=$EXPECTED"
    echo "completed_incast=$got"
    echo "trace_complete=$trace"
    echo "exit_code=$code"
    echo "wall_seconds=$((t1 - t0))"
    echo "config=$cfg"
    echo "config_sha256=$(sha256sum "$cfg" | cut -d' ' -f1)"
    echo "topology_sha256=$(sha256sum "$D/$(cfgval TOPOLOGY_FILE)" 2>/dev/null | cut -d' ' -f1)"
    echo "flow_file_sha256=$(sha256sum "$D/$(cfgval FLOW_FILE)" 2>/dev/null | cut -d' ' -f1)"
    echo "round_schedule_sha256=$(sha256sum "$D/$(cfgval ROUND_SCHEDULE_FILE)" 2>/dev/null | cut -d' ' -f1)"
    echo "cbap_link_sha256=$(sha256sum "$D/$(cfgval CBAP_LINK_FILE)" 2>/dev/null | cut -d' ' -f1)"
    echo "cbap_path_sha256=$(sha256sum "$D/$(cfgval CBAP_PATH_FILE)" 2>/dev/null | cut -d' ' -f1)"
    echo "binary_sha256=$(sha256sum build/scratch/third 2>/dev/null | cut -d' ' -f1)"
    echo "git_commit=$(git -C /work rev-parse HEAD 2>/dev/null || echo unknown)"
    echo "git_dirty=$(git -C /work status --porcelain 2>/dev/null | wc -l)"
    echo "output_dir=$D/$out"
    echo "log=$LOGS/${name}.log"
  } > "$LOGS/${name}.manifest"

  if [ "$code" -eq 0 ] && [ "$got" -eq "$EXPECTED" ] && [ "$trace" = "ok" ]; then
    touch "$flag"
    echo "OK   $name ($got/$EXPECTED incast, $((t1 - t0))s)"
  else
    echo "FAIL $name (exit=$code, $got/$EXPECTED incast, trace=$trace)"
    grep -E "CONFIG_ERROR|assert|terminate|LOG_TRUNCATED" "$LOGS/${name}.log" | head -1
    return 1
  fi
}

# Strictly serial: one simulation at a time.  Two concurrent ns-3 runs on two
# cores skewed wall-clock badly and the container was repeatedly killed under
# the memory pressure of the larger scenarios.
if [ "${MAX_JOBS:-1}" != "1" ]; then
  echo "MAX_JOBS must be 1 (got ${MAX_JOBS}); refusing to run concurrently"
  exit 1
fi
FAILED=0
for seed in $SEEDS; do
  for algo in dcqcn dctcp timely hpcc cbapsba; do
    run_cell "$algo" "$seed" || FAILED=$((FAILED + 1))
    # Stop the rest of this scenario on the first failure so an anomaly is
    # reported rather than buried under four more cells.
    if [ "$FAILED" -gt 0 ]; then
      echo "===== $TAG ABORTED after a failed cell; not running the rest ====="
      exit 1
    fi
  done
  echo "===== seed $seed complete ($(ls "$LOGS"/m_*_${TAG}_seed${seed}.done 2>/dev/null | wc -l) cells done) ====="
done

TOTAL=$(ls "$LOGS"/m_*_${TAG}_seed${seed}.done 2>/dev/null | wc -l)
echo ""
echo "===== MATRIX $TAG COMPLETE: $TOTAL cells done ====="
echo "extract with: python2 $D/metrics.py $TAG"
