#!/bin/bash
# Build RUN_MANIFEST_12CELL.txt and re-verify the pg / config-equivalence
# invariants.  Uses the ALREADY GENERATED and validated ckpt2_* configs; does not
# regenerate them.
set -u
cd /workspaces/yunxiao/simulation/experiment/scheme1_sba || exit 2

D=CHECKPOINT_PROVENANCE
MAN=$D/RUN_MANIFEST_12CELL.txt
BIN=../../build/scratch/third
LIB=../../build/libns3.18-point-to-point-debug.so

sha() { sha256sum "$1" 2>/dev/null | cut -d' ' -f1; }

BINSHA=$(sha $BIN)
LIBSHA=$(sha $LIB)
V2SHA=$(sha independent_acceptance_v2.py)
R1SHA=$(sha r1_gates_v4.py)
LEGSHA=$(sha independent_acceptance.py)
AVAIL=$(df -h /workspaces | tail -1 | awk '{print $4}')

{
  echo "RUN_MANIFEST_12CELL"
  echo "generated_utc=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "git_head=$(cd /workspaces/yunxiao && git rev-parse HEAD)"
  echo "binary_sha=$BINSHA"
  echo "libns3_sha=$LIBSHA"
  echo "v2_entry_sha=$V2SHA"
  echo "r1_gates_v4_sha=$R1SHA"
  echo "legacy_checker_sha=$LEGSHA"
  echo "disk_available_before_batch=$AVAIL"
  echo "MAX_JOBS=1"
  echo ""
  printf "%-22s %-9s %-8s %-8s %-8s %-8s %s\n" \
    cell algo cfg_sha flow_sha link_sha path_sha output
  for s in 1 2 3 4 5 6; do
    for a in cbap dcqcn; do
      c="ckpt2_${a}_s${s}.txt"
      [ -f "$c" ] || { echo "MISSING $c"; continue; }
      f=$(grep -m1 '^FLOW_FILE' "$c" | awk '{print $2}')
      l=$(grep -m1 '^CBAP_LINK_FILE' "$c" | awk '{print $2}')
      p=$(grep -m1 '^CBAP_PATH_FILE' "$c" | awk '{print $2}')
      printf "%-22s %-9s %-8.8s %-8.8s %-8.8s %-8.8s %s\n" \
        "s${s}" "$a" "$(sha "$c")" "$(sha "$f")" \
        "$(sha "$l")" "$(sha "$p")" "ckpt2_${a}_s${s}_out"
    done
  done
  echo ""
  echo "=== FULL SHAs ==="
  for s in 1 2 3 4 5 6; do
    for a in cbap dcqcn; do
      c="ckpt2_${a}_s${s}.txt"
      [ -f "$c" ] && echo "$(sha "$c")  $c"
    done
  done
  for s in 1 2 3 4 5 6; do
    for x in s${s}_flow.txt s${s}_cbap_link.txt s${s}_cbap_path.txt; do
      [ -f "$x" ] && echo "$(sha "$x")  $x"
    done
  done
} > "$MAN"

echo "=== pg CHECK: every flow in every scenario must be pg=3, zero pg=0 ==="
PGBAD=0
for s in 1 2 3 4 5 6; do
  f=s${s}_flow.txt
  tot=$(awk 'NR>1' "$f" | wc -l)
  p3=$(awk 'NR>1 && $3==3' "$f" | wc -l)
  p0=$(awk 'NR>1 && $3==0' "$f" | wc -l)
  other=$((tot-p3))
  printf "  %-16s flows=%-4s pg3=%-4s pg0=%-3s other=%s\n" "$f" "$tot" "$p3" "$p0" "$other"
  [ "$p0" -ne 0 ] && PGBAD=$((PGBAD+1))
  [ "$other" -ne 0 ] && PGBAD=$((PGBAD+1))
done
echo "  pg violations: $PGBAD"
{ echo ""; echo "=== pg CHECK: pg0_count=0 across all six scenarios, violations=$PGBAD ==="; } >> "$MAN"

echo ""
echo "=== CBAP vs DCQCN: only algorithm/controller fields may differ ==="
ALLOWED='CC_MODE|CBAP_ENABLE|CBAP_QUEUE_CONTROLLER_ENABLE'
EQBAD=0
for s in 1 2 3 4 5 6; do
  a="ckpt2_cbap_s${s}.txt"; b="ckpt2_dcqcn_s${s}.txt"
  [ -f "$a" ] && [ -f "$b" ] || continue
  d=$(diff <(sed "s#ckpt2_cbap_s${s}_out#OUT#g" "$a") \
           <(sed "s#ckpt2_dcqcn_s${s}_out#OUT#g" "$b") \
       | grep -E '^[<>]' | awk '{print $2}' | sort -u)
  bad=$(echo "$d" | grep -vE "^($ALLOWED)$" | grep -v '^$' || true)
  if [ -n "$bad" ]; then
    echo "  s${s}: UNEXPECTED DIFF -> $(echo $bad | tr '\n' ' ')"
    EQBAD=$((EQBAD+1))
  else
    echo "  s${s}: OK (differs only in: $(echo $d | tr '\n' ' '))"
  fi
done
echo "  equivalence violations: $EQBAD"

echo ""
echo "=== topology / flow / link / seed identity across the pair ==="
for s in 1 2 3 4 5 6; do
  a="ckpt2_cbap_s${s}.txt"; b="ckpt2_dcqcn_s${s}.txt"
  [ -f "$a" ] && [ -f "$b" ] || continue
  ok=1
  for k in TOPOLOGY_FILE FLOW_FILE CBAP_LINK_FILE CBAP_PATH_FILE SIM_SEED \
           SIMULATOR_STOP_TIME QLEN_MON_START QLEN_MON_END APP_RATE_CAP_BPS \
           KMIN KMAX PMAX PAUSE_TIME BUFFER_SIZE ENABLE_QCN; do
    va=$(grep -m1 "^$k " "$a" | awk '{print $2}')
    vb=$(grep -m1 "^$k " "$b" | awk '{print $2}')
    [ "$va" = "$vb" ] || { echo "  s${s} $k differs: $va vs $vb"; ok=0; }
  done
  [ "$ok" = 1 ] && echo "  s${s}: all shared params identical"
done

{ echo "=== CBAP vs DCQCN equivalence violations=$EQBAD ==="; } >> "$MAN"

echo ""
echo "=== MANIFEST ==="
wc -l "$MAN"
head -22 "$MAN"
echo ""
[ "$PGBAD" -eq 0 ] && [ "$EQBAD" -eq 0 ] && echo "GATE OK: pg and equivalence clean" || { echo "GATE FAILED"; exit 3; }
