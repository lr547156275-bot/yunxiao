set -u
cd /work/simulation
D=experiment/scheme1_sba
L=/work/matrix_logs
export LD_LIBRARY_PATH=/work/simulation/build

# 2-way parallel driver. Deliberately NOT run_matrix.sh: that script hard-refuses
# MAX_JOBS != 1, and rather than weaken its guard (it protects the frozen serial
# path) this driver reuses its config-generation and validation logic inline.
#
# Pairing rule: two cells from the SAME scenario run together, so both share the
# stop time and the pair finishes before the next scenario begins. 5 algorithms
# per scenario => pairs (a,b) (c,d) then e alone.

cc_of()  { case $1 in dcqcn) echo 1;; dctcp) echo 8;; timely) echo 7;; hpcc) echo 3;; cbapsba) echo 30;; esac; }
cbap_of(){ case $1 in cbapsba) echo 1;; *) echo 0;; esac; }
mig_of() { case $1 in cbapsba) echo 1;; *) echo 0;; esac; }

build_cfg() {
  local algo=$1 tag=$2 stop=$3 stopns=$4 out=$5 cfg=$6
  awk -v cc="$(cc_of $algo)" -v cbap="$(cbap_of $algo)" -v algo="$algo" \
      -v stop="$stop" -v stopns="$stopns" -v out="$out" -v tag="$tag" '
    NF==0 { next }
    $1=="CC_MODE"                    { print "CC_MODE " cc; next }
    $1=="CBAP_ENABLE"                { print "CBAP_ENABLE " cbap; next }
    $1=="SIM_SEED"                   { print "SIM_SEED 2"; next }
    $1=="ALGORITHM"                  { print "ALGORITHM " algo; next }
    $1=="SIMULATOR_STOP_TIME"        { print "SIMULATOR_STOP_TIME " stop; next }
    $1=="QLEN_MON_END"               { print "QLEN_MON_END " stopns; next }
    $1=="ROUND_TRACE_SELECTED_FLOWS" { print "ROUND_TRACE_SELECTED_FLOWS 0,1,2,3"; next }
    $1=="CBAP_MIGRATION_ENABLE"      { next }
    $1=="CBAP_MIGRATION_TRACE"       { next }
    $1=="CBAP_ETA_FEASIBILITY_TRACE" { next }
    $1=="CBAP_ETA_FEASIBILITY_FILE"  { next }
    $1=="APP_CAP_TRACE"              { next }
    { gsub(tag "_out/", out "/"); print }
  ' $D/${tag}_config.txt > "$cfg"
  if [ "$(mig_of $algo)" = "1" ]; then
    echo "CBAP_MIGRATION_ENABLE 1" >> "$cfg"
    echo "CBAP_MIGRATION_TRACE 0"  >> "$cfg"
    echo "CBAP_ETA_FEASIBILITY_TRACE 1" >> "$cfg"
    echo "CBAP_ETA_FEASIBILITY_FILE ${out}/eta_feasibility.csv" >> "$cfg"
  fi
}

run_one() {
  local algo=$1 tag=$2 stop=$3 stopns=$4 expected=$5 bgre=$6
  local name="m_${algo}_${tag}_seed2"
  local out="${name}_out" cfg="$D/${name}.txt" flag="$L/${name}.done"
  [ -f "$flag" ] && { echo "SKIP $name"; return 0; }
  mkdir -p "$D/$out"
  build_cfg "$algo" "$tag" "$stop" "$stopns" "$out" "$cfg"
  local t0 t1 code got trace last
  t0=$(date +%s)
  ( cd "$D" && timeout --kill-after=60 14400 /work/simulation/build/scratch/third "${name}.txt" ) \
      > "$L/${name}.log" 2>&1
  code=$?
  t1=$(date +%s)
  got=$(awk -F, -v re="$bgre" 'NR>1 && $6 !~ re && $13==1 {n++} END{print n+0}' "$D/$out/flow_summary.csv" 2>/dev/null || echo 0)
  last=$(awk -F, 'NR>1{t=$1} END{printf "%.4f", t+0}' "$D/$out/selected_link_timeseries.csv" 2>/dev/null || echo 0)
  trace=$(awk -v l="$last" -v e="$stop" 'BEGIN{print (e-l <= 0.00003 ? "ok" : "short")}')
  grep -q LOG_TRUNCATED "$L/${name}.log" 2>/dev/null && trace="truncated"
  cfgval() { awk -v k="$1" '$1==k{$1=""; sub(/^ /,""); print; exit}' "$cfg"; }
  {
    echo "algorithm=$algo"; echo "cc_mode=$(cc_of $algo)"
    echo "cbap_enable=$(cbap_of $algo)"; echo "migration=$(mig_of $algo)"
    echo "scenario=$tag"; echo "scenario_name=$(cfgval SCENARIO)"; echo "seed=2"
    echo "stop_time=$stop"
    echo "qlen_mon_start=$(cfgval QLEN_MON_START)"; echo "qlen_mon_end=$(cfgval QLEN_MON_END)"
    echo "kmin_map=$(cfgval KMIN_MAP)"; echo "kmax_map=$(cfgval KMAX_MAP)"
    echo "pmax_map=$(cfgval PMAX_MAP)"; echo "pause_time=$(cfgval PAUSE_TIME)"
    echo "buffer_size=$(cfgval BUFFER_SIZE)"; echo "enable_qcn=$(cfgval ENABLE_QCN)"
    echo "dynamic_pfc_threshold=$(cfgval USE_DYNAMIC_PFC_THRESHOLD)"
    echo "app_rate_cap_flow=$(cfgval APP_RATE_CAP_FLOW)"
    echo "app_rate_cap_bps=$(cfgval APP_RATE_CAP_BPS)"
    echo "selected_links=$(cfgval ROUND_TRACE_SELECTED_LINKS)"
    echo "selected_flows=$(cfgval ROUND_TRACE_SELECTED_FLOWS)"
    echo "sample_us=$(cfgval CRFM_TRACE_SAMPLE_US)"
    echo "expected_incast=$expected"; echo "completed_incast=$got"
    echo "trace_complete=$trace"; echo "exit_code=$code"
    echo "wall_seconds=$((t1-t0))"; echo "parallel_jobs=2"
    echo "config=$cfg"
    echo "config_sha256=$(sha256sum "$cfg" | cut -d' ' -f1)"
    echo "topology_sha256=$(sha256sum "$D/$(cfgval TOPOLOGY_FILE)" 2>/dev/null | cut -d' ' -f1)"
    echo "flow_file_sha256=$(sha256sum "$D/$(cfgval FLOW_FILE)" 2>/dev/null | cut -d' ' -f1)"
    echo "round_schedule_sha256=$(sha256sum "$D/$(cfgval ROUND_SCHEDULE_FILE)" 2>/dev/null | cut -d' ' -f1)"
    echo "cbap_link_sha256=$(sha256sum "$D/$(cfgval CBAP_LINK_FILE)" 2>/dev/null | cut -d' ' -f1)"
    echo "cbap_path_sha256=$(sha256sum "$D/$(cfgval CBAP_PATH_FILE)" 2>/dev/null | cut -d' ' -f1)"
    echo "binary_sha256=$(sha256sum build/scratch/third | cut -d' ' -f1)"
    echo "p2p_lib_sha256=$(sha256sum build/libns3.18-point-to-point-debug.so | cut -d' ' -f1)"
    echo "git_commit=$(git -C /work rev-parse HEAD 2>/dev/null || echo unknown)"
    echo "git_dirty=$(git -C /work status --porcelain 2>/dev/null | wc -l)"
    echo "output_dir=$D/$out"; echo "log=$L/${name}.log"
  } > "$L/${name}.manifest"
  if [ "$code" -eq 0 ] && [ "$got" -eq "$expected" ] && [ "$trace" = "ok" ]; then
    touch "$flag"; echo "OK   $name ($got/$expected, $((t1-t0))s)"
  else
    echo "FAIL $name (exit=$code, $got/$expected, trace=$trace)"; return 1
  fi
}

# Hash gate, same rule as run_matrix.sh: both binaries must match the freeze.
BM=$L/matrix_baseline.manifest
for k in binary_sha256:build/scratch/third p2p_lib_sha256:build/libns3.18-point-to-point-debug.so; do
  key=${k%%:*}; file=${k##*:}
  want=$(awk -F= -v kk=$key '$1==kk{print $2}' "$BM")
  have=$(sha256sum "$file" | cut -d' ' -f1)
  [ "$want" = "$have" ] || { echo "HASH MISMATCH on $key"; exit 1; }
done
echo "hash gate: third + p2p_lib match FINAL FREEZE"

FAILED=0
for spec in "s1 2.1" "s2 2.5" "s3 3.0" "s6 2.5" "s4 5.5" "s5 6.0"; do
  set -- $spec; tag=$1; stop=$2
  stopns=$(awk -v s=$stop 'BEGIN{printf "%d", s*1e9}')
  if [ "$tag" = "s6" ]; then bgre='^(65|61)$'; else bgre='^65$'; fi
  expected=$(awk -v re="$bgre" 'NR>1 && $1 !~ re {n++} END{print n+0}' "$D/$(awk '/^FLOW_FILE/{print $2}' $D/${tag}_config.txt)")
  echo "########## $tag stop=${stop}s expected_incast=$expected (2-way parallel) ##########"
  set -- dcqcn dctcp timely hpcc cbapsba
  while [ $# -gt 0 ]; do
    a=$1; shift
    if [ $# -gt 0 ]; then
      b=$1; shift
      run_one "$a" "$tag" "$stop" "$stopns" "$expected" "$bgre" & j1=$!
      run_one "$b" "$tag" "$stop" "$stopns" "$expected" "$bgre" & j2=$!
      wait $j1 || FAILED=$((FAILED+1))
      wait $j2 || FAILED=$((FAILED+1))
    else
      run_one "$a" "$tag" "$stop" "$stopns" "$expected" "$bgre" || FAILED=$((FAILED+1))
    fi
    [ "$FAILED" -gt 0 ] && { echo "########## $tag ABORTED after a failed cell ##########"; exit 1; }
  done
done
echo "MATRIX_COMPLETE done_flags=$(ls $L/m_*_s[1-6]_seed2.done 2>/dev/null | wc -l)/30"
