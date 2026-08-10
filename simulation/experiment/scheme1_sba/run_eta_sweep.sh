#!/bin/bash
# eta (CBAP_MIGRATION_RELEASE_RATIO) sensitivity sweep on S4.
#
# Purpose: show that CBAP-SBA exposes an explicit, tunable incast-vs-background
# trade-off, which the feedback-driven baselines do not.  eta is the fraction of
# its aggregate rate the old (background) side releases to an arriving batch:
#   rdma-hw.cc:1870  oldShare = (1 - eta) * oldAggregate
# so larger eta hands the collective more capacity, sooner.
#
# Usage:
#   cd <repo>/simulation
#   bash experiment/scheme1_sba/run_eta_sweep.sh              # 0.20 0.35 0.65 0.80
#   bash experiment/scheme1_sba/run_eta_sweep.sh 0.20 0.80    # explicit subset
#
# Deliberate properties, mirroring run_matrix.sh:
#   * ONLY CBAP_MIGRATION_RELEASE_RATIO varies.  Everything else -- topology,
#     flow file, seed, MIN_RATE, Qmin/Qmax, f_inc/f_dec, ECN/PFC, stop time,
#     QLEN_MON_END, sample interval, CC_MODE -- is inherited unchanged from
#     s4_config.txt, the same base file the main matrix used.
#   * eta=0.50 is NOT run: it is the compiled default (third.cc:159) and
#     s4_config.txt never overrides it, so the main-matrix cell
#     m_cbapsba_s4_seed2 already IS eta=0.50.  It is reused, and the reuse is
#     gated on a config-hash comparison rather than assumed.
#   * Serial only, resumable by .done flag, deletes nothing, per-cell manifest.
#   * No baseline is re-run.  DCQCN/DCTCP/TIMELY/HPCC S4 reference points come
#     from the existing final_results.csv.
set -u

SIM=/workspaces/yunxiao/simulation
D=experiment/scheme1_sba
LOGS=/workspaces/yunxiao/matrix_logs
TAG=s4
STOP=5.5
SEED=2

ETAS="$*"
[ -n "$ETAS" ] || ETAS="0.20 0.35 0.65 0.80"

cd "$SIM" || { echo "cannot cd $SIM"; exit 1; }
mkdir -p "$LOGS"

BASECFG=$D/${TAG}_config.txt
[ -f "$BASECFG" ] || { echo "missing $BASECFG"; exit 1; }
FLOWFILE=$D/$(awk '/^FLOW_FILE/{print $2}' "$BASECFG")
[ -f "$FLOWFILE" ] || { echo "missing flow file $FLOWFILE"; exit 1; }

# S4 has a single background source (node 65); every other flow is incast.
EXPECTED=$(awk 'NR>1 && $1 != 65 {n++} END{print n+0}' "$FLOWFILE")
STOPNS=$(python3 -c "print(int(float('$STOP')*1e9))")
SAMPLE_S=$(awk '/^CRFM_TRACE_SAMPLE_US/{printf "%.9f", $2/1e6; exit}' "$BASECFG")
[ -n "$SAMPLE_S" ] || SAMPLE_S=0.00001

echo "=== eta sweep on $TAG ==="
echo "  etas          : $ETAS   (0.50 reused from the main matrix)"
echo "  expected incast: $EXPECTED"
echo "  stop / seed   : $STOP s / $SEED"

# ---------------------------------------------------------------- hash gate
# Same rule as the main matrix: refuse to run if the binary or topology moved,
# so sweep cells cannot be silently built from a different binary than the
# eta=0.50 cell they are compared against.
BASE_MF=$LOGS/matrix_baseline.manifest
if [ -f "$BASE_MF" ]; then
  want_topo=$(awk -F= '$1=="topology_sha256"{print $2}' "$BASE_MF")
  want_bin=$(awk -F= '$1=="binary_sha256"{print $2}' "$BASE_MF")
  have_topo=$(sha256sum "$D/topology.txt" | cut -d' ' -f1)
  have_bin=$(sha256sum build/scratch/third | cut -d' ' -f1)
  if [ -n "$want_topo" ] && [ "$want_topo" != "$have_topo" ]; then
    echo "HASH MISMATCH: topology.txt changed since the baseline; refusing"; exit 1
  fi
  if [ -n "$want_bin" ] && [ "$want_bin" != "$have_bin" ]; then
    echo "HASH MISMATCH: build/scratch/third changed since the baseline"
    echo "  baseline=$want_bin"
    echo "  current =$have_bin"
    echo "  The sweep must run on the SAME binary as the eta=0.50 cell."
    echo "  Rebuild from commit $(awk -F= '$1=="git_commit"{print $2}' "$BASE_MF") or"
    echo "  re-run the S4 cbapsba cell too, so all five etas share one binary."
    exit 1
  fi
  echo "  hash gate     : topology + binary match the matrix baseline"
else
  echo "  hash gate     : no baseline manifest; recording current hashes"
fi

# ------------------------------------------------------- eta=0.50 reuse gate
# Requirement: reuse the main-matrix cell only if its configuration is
# genuinely identical to what this sweep would generate at eta=0.50.  Verify by
# regenerating that config into a temp file and diffing, rather than trusting
# that the default was in force.
REF_NAME="m_cbapsba_${TAG}_seed${SEED}"
REF_MF=$LOGS/${REF_NAME}.manifest

build_cfg() {
  # $1=eta  $2=out_dir  $3=dest_cfg   ("" for eta => omit the key entirely,
  # which is exactly what the main matrix did)
  local eta=$1 out=$2 cfg=$3
  awk -v seed="$SEED" -v stop="$STOP" -v stopns="$STOPNS" -v out="$out" \
      -v tag="$TAG" '
    NF==0 { next }
    $1=="CC_MODE"                    { print "CC_MODE 30"; next }
    $1=="CBAP_ENABLE"                { print "CBAP_ENABLE 1"; next }
    $1=="SIM_SEED"                   { print "SIM_SEED " seed; next }
    $1=="ALGORITHM"                  { print "ALGORITHM cbapsba"; next }
    $1=="SIMULATOR_STOP_TIME"        { print "SIMULATOR_STOP_TIME " stop; next }
    $1=="QLEN_MON_END"               { print "QLEN_MON_END " stopns; next }
    $1=="ROUND_TRACE_SELECTED_FLOWS" { print "ROUND_TRACE_SELECTED_FLOWS 0,1,2,3"; next }
    $1=="CBAP_MIGRATION_ENABLE"      { next }
    $1=="CBAP_MIGRATION_TRACE"       { next }
    $1=="CBAP_MIGRATION_RELEASE_RATIO" { next }
    $1=="APP_CAP_TRACE"              { next }
    { gsub(tag "_out/", out "/"); print }
  ' "$BASECFG" > "$cfg"
  echo "CBAP_MIGRATION_ENABLE 1" >> "$cfg"
  echo "CBAP_MIGRATION_TRACE 0" >> "$cfg"
  # Appending is purely additive: the key is absent from s4_config.txt, so no
  # other setting can be perturbed by adding it.
  if [ -n "$eta" ]; then
    echo "CBAP_MIGRATION_RELEASE_RATIO $eta" >> "$cfg"
  fi
}

REUSE_OK=0
if [ -f "$REF_MF" ] && [ -f "$LOGS/${REF_NAME}.done" ]; then
  want_cfg=$(awk -F= '$1=="config_sha256"{print $2}' "$REF_MF")
  tmp=$(mktemp)
  build_cfg "" "${REF_NAME}_out" "$tmp"
  have_cfg=$(sha256sum "$tmp" | cut -d' ' -f1)
  rm -f "$tmp"
  if [ "$want_cfg" = "$have_cfg" ]; then
    REUSE_OK=1
    echo "  eta=0.50      : REUSE $REF_NAME (config hash identical: ${want_cfg:0:12}...)"
  else
    echo "  eta=0.50      : config hash DIFFERS from the matrix cell"
    echo "                  matrix=$want_cfg"
    echo "                  now   =$have_cfg"
    echo "                  -> 0.50 must be re-run explicitly; add it to the eta list."
  fi
else
  echo "  eta=0.50      : main-matrix cell or manifest absent; add 0.50 to the eta list"
fi

# ------------------------------------------------------------ helper: gates
completed_incast() {
  local f=$1
  [ -f "$f" ] || { echo 0; return; }
  # column 6 = src, 13 = completed -- identical to run_matrix.sh
  awk -F, 'NR>1 && $6 != 65 && $13 == 1 {n++} END{print n+0}' "$f" 2>/dev/null || echo 0
}

trace_complete() {
  local ts=$1 log=$2
  if grep -q "LOG_TRUNCATED" "$log" 2>/dev/null; then echo "truncated"; return; fi
  [ -f "$ts" ] || { echo "missing"; return; }
  local last
  last=$(awk -F, 'NR>1{t=$1} END{print t+0}' "$ts")
  awk -v l="$last" -v e="$STOP" -v s="$SAMPLE_S" \
    'BEGIN{ if (e - l <= s*2 + 1e-9) print "ok"; else printf "short(%.6f<%.6f)\n", l, e }'
}

# --------------------------------------------------------------- eta arm
eta_tag() { echo "$1" | sed 's/\.//'; }   # 0.20 -> 020

run_eta() {
  local eta=$1
  local et; et=$(eta_tag "$eta")
  local name="m_cbapsba_${TAG}_eta${et}_seed${SEED}"
  local out="${name}_out"
  local cfg="$D/${name}.txt"
  local flag="$LOGS/${name}.done"
  if [ -f "$flag" ]; then echo "SKIP $name"; return 0; fi

  mkdir -p "$D/$out"
  build_cfg "$eta" "$out" "$cfg"

  # Guard: the generated config must differ from the eta=0.50 reference in
  # exactly one line -- the release-ratio key.  Anything else means the sweep
  # perturbed a frozen parameter, and it stops rather than produce data.
  local tmp diffn
  tmp=$(mktemp)
  build_cfg "" "$out" "$tmp"
  diffn=$(diff "$tmp" "$cfg" | grep -c '^[<>]' || true)
  rm -f "$tmp"
  if [ "$diffn" -ne 1 ]; then
    echo "FAIL $name: config differs from the eta=0.50 form in $diffn lines (expected 1)"
    echo "  refusing to run -- only CBAP_MIGRATION_RELEASE_RATIO may vary"
    return 1
  fi

  local t0 t1
  cd "$SIM/$D" || return 1
  t0=$(date +%s)
  timeout --kill-after=60 "${CELL_TIMEOUT:-14400}" \
      env LD_LIBRARY_PATH="$SIM/build:$SIM/build/compat" \
      "$SIM/build/scratch/third" "${name}.txt" \
      > "$LOGS/${name}.log" 2>&1
  local code=$?
  t1=$(date +%s)
  cd "$SIM" || return 1

  local got trace
  got=$(completed_incast "$D/$out/flow_summary.csv")
  trace=$(trace_complete "$D/$out/selected_link_timeseries.csv" "$LOGS/${name}.log")

  local g=$cfg
  cfgval() { awk -v k="$1" '$1==k{$1=""; sub(/^ /,""); print; exit}' "$g"; }
  {
    echo "algorithm=cbapsba"
    echo "sweep=eta"
    echo "eta=$eta"
    echo "cc_mode=30"
    echo "cbap_enable=1"
    echo "migration=1"
    echo "scenario=$TAG"
    echo "scenario_name=$(cfgval SCENARIO)"
    echo "seed=$SEED"
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
    echo "release_ratio=$(cfgval CBAP_MIGRATION_RELEASE_RATIO)"
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
    echo "git_commit=$(git -C "$SIM" rev-parse HEAD 2>/dev/null || echo unknown)"
    echo "git_dirty=$(git -C "$SIM" status --porcelain 2>/dev/null | wc -l)"
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

if [ "${MAX_JOBS:-1}" != "1" ]; then
  echo "MAX_JOBS must be 1 (got ${MAX_JOBS}); refusing to run concurrently"
  exit 1
fi

echo ""
FAILED=0
for eta in $ETAS; do
  run_eta "$eta" || FAILED=$((FAILED + 1))
  if [ "$FAILED" -gt 0 ]; then
    echo "===== eta sweep ABORTED after a failed cell ====="
    exit 1
  fi
done

echo ""
echo "=== eta sweep complete: $(ls "$LOGS"/m_cbapsba_${TAG}_eta*_seed${SEED}.done 2>/dev/null | wc -l) new cells ==="
if [ "$REUSE_OK" = "1" ]; then
  echo "    plus eta=0.50 reused from $REF_NAME"
fi
echo "Next: python2 $D/eta_metrics.py"
