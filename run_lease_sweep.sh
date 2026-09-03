#!/bin/bash
# LEASE SENSITIVITY SWEEP: {200G,400G}-S2 x CBAP_SBA_LEASE_US {500,2000}.
# Mirrors run_v2matrix.sh conventions.  Binary gate: accept if sha in
# REGV4_OK, or in our REGRESSION_OK, or if a byte-regression against the
# frozen fm200g/fm400g_s2_cbap baselines passes (never writes old dirs).
# Run inside the hpcc-build container:  bash /work/run_lease_sweep.sh
set -u
export LD_LIBRARY_PATH=/work/simulation/build:${LD_LIBRARY_PATH:-}
BIN=/work/simulation/build/scratch/third
V2=/work/v2_400g
NEW=/work/v2_lease
mkdir -p "$NEW/configs" "$NEW/results" "$NEW/logs" "$NEW/regression"

# --- gate 2 first: baselines must exist (regression needs them too) ------
for b in fm200g_s2_cbap fm400g_s2_cbap; do
  [ -s "$V2/results/$b/flow_timing.csv" ] \
    || { echo "BASELINE MISSING: $b"; exit 6; }
done

# --- gate 3: disk ---------------------------------------------------------
free=$(df -BG /work | awk 'NR==2{gsub("G","",$4); print $4}')
[ "$free" -ge 5 ] || { echo "DISK_GUARD_FAIL (${free}G free < 5G)"; exit 9; }

# --- gate 1: binary must be the matrix binary OR byte-equivalent to it ---
regress() {                       # $1 = baseline tag; byte-compare 5 CSVs
  local src=$1 rdir=$NEW/regression/$src
  if [ -f "$rdir/PASS" ]; then echo "REGRESS SKIP $src (passed)"; return 0; fi
  mkdir -p "$rdir"
  sed "s#$V2/results/$src#$rdir#g" "$V2/configs/$src.txt" > "$rdir/cfg.txt"
  echo "REGRESS RUN $src (rerun to scratch, ~10 min)"
  timeout -k 60 7200 "$BIN" "$rdir/cfg.txt" > "$rdir/run.log" 2>&1 \
    || { echo "REGRESS RUN FAIL $src rc=$?"; tail -3 "$rdir/run.log"; return 1; }
  local f bad=0
  for f in flow_timing.csv flow_summary.csv rate_transition.csv \
           pfc_events.csv round_summary.csv; do
    if cmp -s "$V2/results/$src/$f" "$rdir/$f"; then
      echo "  identical $f"
    else
      echo "  DIFFERS   $f"; bad=1
    fi
  done
  [ $bad -eq 0 ] && touch "$rdir/PASS"
  return $bad
}

cursha=$(sha256sum "$BIN" | awk '{print $1}')
if grep -q "$cursha" "$V2/logs/REGV4_OK" 2>/dev/null \
   || grep -q "$cursha" "$NEW/logs/REGRESSION_OK" 2>/dev/null; then
  echo "binary ok: $cursha"
else
  echo "binary $cursha not yet validated -- byte-regression vs frozen baselines"
  if regress fm200g_s2_cbap && regress fm400g_s2_cbap; then
    echo "$cursha  $(date -u +%FT%TZ)" >> "$NEW/logs/REGRESSION_OK"
    echo "REGRESSION PASS -- binary behaviourally identical, accepted"
  else
    echo "REGRESSION FAILED: current binary is NOT equivalent to the matrix binary."
    echo "Do NOT run lease cells.  Send the DIFFERS list above + 'git log --oneline -5'."
    exit 5
  fi
fi

gen_cfg() {                       # $1=src tag  $2=lease_us  $3=new tag
  local src=$1 lease=$2 tag=$3
  sed -e "s#$V2/results/$src#$NEW/results/$tag#g" \
      -e "s/^CBAP_SBA_LEASE_US .*/CBAP_SBA_LEASE_US $lease/" \
      "$V2/configs/$src.txt" > "$NEW/configs/$tag.txt"
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

echo "=== SUMMARY ==="
for t in ls200g_s2_cbap_l0500 ls200g_s2_cbap_l2000 \
         ls400g_s2_cbap_l0500 ls400g_s2_cbap_l2000; do
  d=$NEW/results/$t
  printf "%-24s DONE=[%s] flows=%s lease_hits(heur)=%s\n" "$t" \
    "$(cat "$d/DONE" 2>/dev/null || echo MISSING)" \
    "$(awk 'END{print NR-1}' "$d/flow_timing.csv" 2>/dev/null)" \
    "$(grep -ci lease "$d/sba_events.csv" 2>/dev/null)"
done

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
