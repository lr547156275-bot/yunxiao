#!/bin/bash
# Step B + C: freeze the v2 boundary model, then generate and audit ckpt3.
#
# ckpt3 = the 12 checkpoint cells (S1-S6 x CBAP/DCQCN) with the MULTI-LINK
# per-packet recorder enabled on every cell.  ckpt_* and ckpt2_* are only
# LABELLED, never deleted or overwritten.
#
# Input-key allow-list is explicit: the five keys the simulator READS are never
# prefixed with an output directory.  That defect (all 12 cells unable to read
# their topology) was caught by the manifest audit last round.
set -u
cd /workspaces/yunxiao/simulation/experiment/scheme1_sba || exit 2

D=CHECKPOINT_PROVENANCE
INPUT_KEYS='TOPOLOGY_FILE|FLOW_FILE|CBAP_LINK_FILE|CBAP_PATH_FILE|ROUND_SCHEDULE_FILE'
QC_SOFT=0.5; QC_BOOST=0.30; QC_HGUARD=175; QC_HARD=838.86; QC_MSAFE=67072

sha() { sha256sum "$1" 2>/dev/null | cut -d' ' -f1; }

# ---------- label the superseded config generations ----------------------
for d in ckpt_cbap ckpt_dcqcn; do
  for s in 1 2 3 4 5 6; do
    f="${d}_s${s}.txt"
    [ -f "$f" ] || continue
    m="${d}_s${s}.INVALID_CONFIG_PATH_GENERATOR.txt"
    [ -f "$m" ] || {
      echo "STATUS=INVALID_CONFIG_PATH_GENERATOR" > "$m"
      echo "REASON=generator rewrote INPUT keys into the output dir; cells could not read topology/flow/link/path" >> "$m"
      echo "CONFIG_SHA=$(sha "$f")" >> "$m"
      echo "RETAINED=yes" >> "$m"
    }
  done
done
for s in 1 2 3 4 5 6; do
  for a in cbap dcqcn; do
    f="ckpt2_${a}_s${s}.txt"
    [ -f "$f" ] || continue
    m="ckpt2_${a}_s${s}.SUPERSEDED.txt"
    [ -f "$m" ] || {
      echo "STATUS=SUPERSEDED_MISSING_UNIFORM_TX_RECORDER" > "$m"
      echo "REASON=no TX_SERIALIZATION_TRACE_FILE; R-1a/b/c not evaluable" >> "$m"
      echo "CONFIG_SHA=$(sha "$f")" >> "$m"
      echo "SUPERSEDED_BY=ckpt3_${a}_s${s}.txt" >> "$m"
      echo "RETAINED=yes" >> "$m"
    }
  done
done
echo "labelled ckpt_* (INVALID_CONFIG_PATH_GENERATOR) and ckpt2_* (SUPERSEDED)"

# ---------- generate ckpt3 ---------------------------------------------
for s in 1 2 3 4 5 6; do
  base="s${s}_config.txt"
  [ -f "$base" ] || { echo "MISSING $base"; exit 2; }
  for a in cbap dcqcn; do
    out="ckpt3_${a}_s${s}_out"
    cfg="ckpt3_${a}_s${s}.txt"
    rm -rf "$out"; mkdir -p "$out"
    awk -v o="$out" -v ik="$INPUT_KEYS" '
      { if ($1 ~ /_FILE$/ && $1 !~ ("^(" ik ")$") && NF >= 2) {
          n = split($2, p, "/"); print $1 " " o "/" p[n]; next }
        print }' "$base" > "$cfg"
    if [ "$a" = "cbap" ]; then CCM=30; CBE=1; QCE=1; else CCM=1; CBE=0; QCE=0; fi
    for kv in "CC_MODE $CCM" "CBAP_ENABLE $CBE" \
              "CBAP_QUEUE_CONTROLLER_ENABLE $QCE" \
              "CBAP_QC_SOFT_FRACTION $QC_SOFT" \
              "CBAP_QC_MAX_BOOST_RATIO $QC_BOOST" \
              "CBAP_QC_H_GUARD_US $QC_HGUARD" \
              "CBAP_QC_APP_HARD_DELAY_US $QC_HARD" \
              "CBAP_QC_SAFETY_MARGIN_BYTES $QC_MSAFE" \
              "CBAP_QC_TRACE_FILE ${out}/qc_trace.csv" \
              "CBAP_DELAY_CREDIT_ENABLE 0" \
              "TX_SERIALIZATION_TRACE_FILE ${out}/tx_serialization.csv"; do
      k=${kv%% *}
      if grep -q "^${k}[[:space:]]" "$cfg"; then
        sed -i "s#^${k}[[:space:]].*#${kv}#" "$cfg"
      else
        echo "$kv" >> "$cfg"
      fi
    done
  done
done
echo "generated 12 ckpt3 cells"

# ---------- audit -----------------------------------------------------
echo ""
echo "=== AUDIT 1: input keys resolve to REAL files ==="
BAD=0
for s in 1 2 3 4 5 6; do for a in cbap dcqcn; do
  c="ckpt3_${a}_s${s}.txt"
  for k in TOPOLOGY_FILE FLOW_FILE ROUND_SCHEDULE_FILE CBAP_LINK_FILE CBAP_PATH_FILE; do
    v=$(grep -m1 "^$k " "$c" | awk '{print $2}')
    [ -z "$v" ] && continue
    [ -f "$v" ] || { echo "  MISSING $c $k -> $v"; BAD=$((BAD+1)); }
  done
done; done
echo "  missing inputs: $BAD"

echo ""
echo "=== AUDIT 2: every cell has a UNIQUE tx trace path ==="
UNIQ=$(for s in 1 2 3 4 5 6; do for a in cbap dcqcn; do
  grep -m1 '^TX_SERIALIZATION_TRACE_FILE ' "ckpt3_${a}_s${s}.txt" | awk '{print $2}'
done; done | sort | uniq | wc -l)
TOT=$(for s in 1 2 3 4 5 6; do for a in cbap dcqcn; do echo x; done; done | wc -l)
echo "  unique tx paths: $UNIQ / $TOT"
[ "$UNIQ" = "$TOT" ] || { echo "  DUPLICATE TX PATH"; BAD=$((BAD+1)); }

echo ""
echo "=== AUDIT 3: pg distribution (all must be 3, zero pg=0) ==="
PG=0
for s in 1 2 3 4 5 6; do
  f=s${s}_flow.txt
  tot=$(awk 'NR>1' "$f" | wc -l); p3=$(awk 'NR>1 && $3==3' "$f" | wc -l)
  p0=$(awk 'NR>1 && $3==0' "$f" | wc -l)
  printf "  %-14s flows=%-4s pg3=%-4s pg0=%s\n" "$f" "$tot" "$p3" "$p0"
  [ "$p0" -eq 0 ] || PG=$((PG+1)); [ "$p3" -eq "$tot" ] || PG=$((PG+1))
done
echo "  pg violations: $PG"

echo ""
echo "=== AUDIT 4: pair shares flow/link/path SHA; differs only in algo keys ==="
EQ=0
for s in 1 2 3 4 5 6; do
  a="ckpt3_cbap_s${s}.txt"; b="ckpt3_dcqcn_s${s}.txt"
  for k in TOPOLOGY_FILE FLOW_FILE ROUND_SCHEDULE_FILE CBAP_LINK_FILE CBAP_PATH_FILE \
           SIM_SEED SIMULATOR_STOP_TIME QLEN_MON_START QLEN_MON_END \
           APP_RATE_CAP_BPS KMIN KMAX PMAX PAUSE_TIME BUFFER_SIZE ENABLE_QCN \
           PACKET_PAYLOAD_SIZE ROUND_TRACE_SELECTED_LINKS; do
    va=$(grep -m1 "^$k " "$a" | awk '{print $2}')
    vb=$(grep -m1 "^$k " "$b" | awk '{print $2}')
    [ "$va" = "$vb" ] || { echo "  s${s} $k: $va vs $vb"; EQ=$((EQ+1)); }
  done
  keys=$(diff <(sed "s#ckpt3_cbap_s${s}_out#OUT#g" "$a") \
              <(sed "s#ckpt3_dcqcn_s${s}_out#OUT#g" "$b") \
         | grep -E '^[<>]' | awk '{print $2}' | sort -u)
  bad=$(echo "$keys" | grep -vE '^(CC_MODE|CBAP_ENABLE|CBAP_QUEUE_CONTROLLER_ENABLE)$' | grep -v '^$' || true)
  if [ -n "$bad" ]; then echo "  s${s}: unexpected diff $(echo $bad|tr '\n' ' ')"; EQ=$((EQ+1));
  else echo "  s${s}: OK (differs only in $(echo $keys|tr '\n' ' '))"; fi
done
echo "  equivalence violations: $EQ"

echo ""
echo "=== AUDIT 5: no output-path leakage between cells ==="
LEAK=0
for s in 1 2 3 4 5 6; do for a in cbap dcqcn; do
  c="ckpt3_${a}_s${s}.txt"
  x=$(grep -oE 'ckpt3_[a-z]+_s[0-9]+_out' "$c" | sort -u | grep -v "^ckpt3_${a}_s${s}_out$" || true)
  [ -n "$x" ] && { echo "  LEAK $c: $x"; LEAK=$((LEAK+1)); }
done; done
echo "  leaks: $LEAK"

echo ""
echo "=== AUDIT 6: expected bottleneck links per scenario (from link file) ==="
for s in 1 2 3 4 5 6; do
  printf "  s%s expected: " "$s"
  awk 'NR>1{printf "%s:%s:%s ",$1,$2,$3}' "s${s}_cbap_link.txt"; echo
done

# ---------- manifest -------------------------------------------------
MAN=$D/RUN_MANIFEST_12CELL_v2.txt
{
  echo "RUN_MANIFEST_12CELL_v2  (ckpt3, uniform multi-link per-packet recorder)"
  echo "generated_utc=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "git_head=$(cd /workspaces/yunxiao && git rev-parse HEAD)"
  echo "MAX_JOBS=1"
  echo "disk_available=$(df -h /workspaces | tail -1 | awk '{print $4}')"
  echo ""
  echo "=== FROZEN TOOLCHAIN ==="
  echo "binary_sha=$(sha ../../build/scratch/third)"
  echo "libns3_sha=$(sha ../../build/libns3.18-point-to-point-debug.so)"
  echo "recorder_ml_sha=$(sha ../../scratch/tx-serialization-recorder-ml.h)"
  echo "recorder_single_sha=$(sha ../../scratch/tx-serialization-recorder.h)  # SUPERSEDED_SINGLE_LINK_RECORDER"
  echo "third_cc_sha=$(sha ../../scratch/third.cc)"
  echo ""
  echo "=== FROZEN CHECKERS ==="
  echo "r1_gates_v4_sha=$(sha r1_gates_v4.py)"
  echo "r1_gates_v4_selftest_sha=$(sha r1_gates_v4_selftest.py)"
  echo "r1_gates_ml_v2_sha=$(sha r1_gates_ml_v2.py)"
  echo "r1_gates_ml_v2_selftest_sha=$(sha r1_gates_ml_v2_selftest.py)"
  echo "r1_gates_ml_v1_sha=$(sha r1_gates_ml.py)  # SUPERSEDED_BY_EXPLICIT_SIMULATION_END_BOUNDARY_MODEL"
  echo "independent_acceptance_sha=$(sha independent_acceptance.py)"
  echo "independent_acceptance_v2_sha=$(sha independent_acceptance_v2.py)"
  echo ""
  echo "=== BOUNDARY MODEL (frozen) ==="
  echo "tick=1 ns (ns-3 Time::NS, TRUNCATING -- verified 838.4->838, 153.6->153)"
  echo "D(L,l)=floor((L*8/C_l)/tick)*tick"
  echo "core_hi_l=min(T_qlen, T_stop - Dmax_l)   [NOT min(T_qlen,T_stop)-Dmax_l]"
  echo ""
  echo "=== PER-CELL ==="
  printf "%-10s %-6s %-9s %-9s %-9s %-9s %-9s %s\n" \
    cell algo cfg_sha flow_sha link_sha path_sha sched_sha tx_trace
  for s in 1 2 3 4 5 6; do
    for a in cbap dcqcn; do
      c="ckpt3_${a}_s${s}.txt"
      f=$(grep -m1 '^FLOW_FILE' "$c" | awk '{print $2}')
      l=$(grep -m1 '^CBAP_LINK_FILE' "$c" | awk '{print $2}')
      p=$(grep -m1 '^CBAP_PATH_FILE' "$c" | awk '{print $2}')
      r=$(grep -m1 '^ROUND_SCHEDULE_FILE' "$c" | awk '{print $2}')
      t=$(grep -m1 '^TX_SERIALIZATION_TRACE_FILE' "$c" | awk '{print $2}')
      printf "%-10s %-6s %-9.9s %-9.9s %-9.9s %-9.9s %-9.9s %s\n" \
        "s$s" "$a" "$(sha "$c")" "$(sha "$f")" "$(sha "$l")" \
        "$(sha "$p")" "$(sha "$r")" "$t"
    done
  done
  echo ""
  echo "=== EXPECTED LINKS PER SCENARIO ==="
  for s in 1 2 3 4 5 6; do
    printf "s%s=" "$s"
    awk 'NR>1{printf "%s:%s:%s,",$1,$2,$3}' "s${s}_cbap_link.txt"; echo
  done
  echo ""
  echo "=== AUDIT RESULTS ==="
  echo "missing_inputs=$BAD  pg_violations=$PG  equivalence_violations=$EQ  leaks=$LEAK"
  echo "unique_tx_paths=$UNIQ/$TOT"
  echo ""
  echo "=== FULL CONFIG SHAs ==="
  for s in 1 2 3 4 5 6; do for a in cbap dcqcn; do
    echo "$(sha "ckpt3_${a}_s${s}.txt")  ckpt3_${a}_s${s}.txt"
  done; done
} > "$MAN"

echo ""
echo "=== MANIFEST: $MAN ($(wc -l < "$MAN") lines) ==="
echo "manifest_sha=$(sha "$MAN")"
echo ""
[ "$BAD" -eq 0 ] && [ "$PG" -eq 0 ] && [ "$EQ" -eq 0 ] && [ "$LEAK" -eq 0 ] \
  && echo "ALL AUDITS PASS" || { echo "AUDIT FAILED"; exit 3; }
