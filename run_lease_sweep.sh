#!/bin/bash
# LEASE SENSITIVITY SWEEP: {200G,400G}-S2 x CBAP_SBA_LEASE_US {500,2000}.
# Mirrors run_v2matrix.sh conventions: same binary gate (REGV4_OK), DONE
# markers, resume-safe, frozen inputs referenced read-only from v2_400g.
# New outputs go ONLY to /work/v2_lease/.  Run inside the hpcc-build
# container:  bash /work/run_lease_sweep.sh
set -u
export LD_LIBRARY_PATH=/work/simulation/build:${LD_LIBRARY_PATH:-}
BIN=/work/simulation/build/scratch/third
V2=/work/v2_400g
NEW=/work/v2_lease
mkdir -p "$NEW/configs" "$NEW/results" "$NEW/logs"

# --- gate 1: identical binary to the formal matrix -----------------------
cursha=$(sha256sum "$BIN" | awk '{print $1}')
grep -q "$cursha" "$V2/logs/REGV4_OK" 2>/dev/null \
  || { echo "BINARY MISMATCH vs REGV4_OK -- do not run"; exit 5; }
echo "binary ok: $cursha"

# --- gate 2: baselines (1 ms cells) must exist ---------------------------
for b in fm200g_s2_cbap fm400g_s2_cbap; do
  [ -f "$V2/results/$b/DONE" ] \
    || { echo "BASELINE MISSING: $b (needed for comparison)"; exit 6; }
done

# --- gate 3: disk --------------------------------------------------------
free=$(df -BG /work | awk 'NR==2{gsub("G","",$4); print $4}')
[ "$free" -ge 5 ] || { echo "DISK_GUARD_FAIL (${free}G free < 5G)"; exit 9; }

gen_cfg() {                       # $1=src tag  $2=lease_us  $3=new tag
  local src=$1 lease=$2 tag=$3
  sed -e "s#$V2/results/$src#$NEW/results/$tag#g" \
      -e "s/^CBAP_SBA_LEASE_US .*/CBAP_SBA_LEASE_US $lease/" \
      "$V2/configs/$src.txt" > "$NEW/configs/$tag.txt"
  # assert: every differing line is the lease line or an output path line
  local stray
  stray=$(diff "$V2/configs/$src.txt" "$NEW/configs/$tag.txt" \
          | grep '^[<>]' | grep -vE "CBAP_SBA_LEASE_US|results/") || true
  [ -z "$stray" ] || { echo "CONFIG DRIFT in $tag:"; echo "$stray"; exit 7; }
  local nlease
  nlease=$(diff "$V2/configs/$src.txt" "$NEW/configs/$tag.txt" \
           | grep -c "CBAP_SBA_LEASE_US")
  [ "$nlease" -eq 2 ] || { echo "LEASE LINE NOT CHANGED in $tag"; exit 7; }
}

run_cell() {                      # $1=tag
  local tag=$1 out=$NEW/results/$tag
  if [ -f "$out/DONE" ]; then echo "SKIP $tag (done)"; return 0; fi
  mkdir -p "$out"
  echo "RUN $tag $(date '+%H:%M:%S')"
  local s; s=$(date +%s)
  timeout -k 60 7200 "$BIN" "$NEW/configs/$tag.txt" \
      > "$NEW/logs/$tag.log" 2>&1
  local rc=$?; local e; e=$(date +%s)
  if [ $rc -eq 0 ] && [ -s "$out/flow_summary.csv" ]; then
    echo "$rc $((e-s))" > "$out/DONE"; echo "OK   $tag $((e-s))s"
  else
    echo "FAIL $tag rc=$rc"; tail -3 "$NEW/logs/$tag.log"
  fi
}

gen_cfg fm200g_s2_cbap  500 ls200g_s2_cbap_l0500
gen_cfg fm200g_s2_cbap 2000 ls200g_s2_cbap_l2000
gen_cfg fm400g_s2_cbap  500 ls400g_s2_cbap_l0500
gen_cfg fm400g_s2_cbap 2000 ls400g_s2_cbap_l2000
echo "4 configs generated + drift-checked"

for t in ls200g_s2_cbap_l0500 ls200g_s2_cbap_l2000 \
         ls400g_s2_cbap_l0500 ls400g_s2_cbap_l2000; do run_cell "$t"; done

# --- summary --------------------------------------------------------------
echo "=== SUMMARY ==="
for t in ls200g_s2_cbap_l0500 ls200g_s2_cbap_l2000 \
         ls400g_s2_cbap_l0500 ls400g_s2_cbap_l2000; do
  d=$NEW/results/$t
  printf "%-24s DONE=[%s] flows=%s lease_hits(heur)=%s\n" "$t" \
    "$(cat "$d/DONE" 2>/dev/null || echo MISSING)" \
    "$(awk 'END{print NR-1}' "$d/flow_timing.csv" 2>/dev/null)" \
    "$(grep -ci lease "$d/sba_events.csv" 2>/dev/null)"
done

# --- evidence tarball (small files only; baselines included for ref) ------
ts=$(date +%Y%m%d_%H%M%S)
tar czf "/work/lease_sweep_evidence_$ts.tar.gz" \
  --exclude='*timeseries*' --exclude='trace_output.txt' \
  -C /work v2_lease \
  v2_400g/results/fm200g_s2_cbap/flow_timing.csv \
  v2_400g/results/fm200g_s2_cbap/sba_events.csv \
  v2_400g/results/fm200g_s2_cbap/feedback_summary.csv \
  v2_400g/results/fm400g_s2_cbap/flow_timing.csv \
  v2_400g/results/fm400g_s2_cbap/sba_events.csv \
  v2_400g/results/fm400g_s2_cbap/feedback_summary.csv
sha256sum "/work/lease_sweep_evidence_$ts.tar.gz"
echo "tarball ready: /work/lease_sweep_evidence_$ts.tar.gz"
