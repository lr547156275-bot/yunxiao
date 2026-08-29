#!/bin/bash
# Rebuild the 12 checkpoint cells, fixing a defect in mk_ckpt_cells.sh.
#
# DEFECT: the previous generator rewrote every key matching *_FILE into the
# cell's output directory, which corrupted the four INPUT keys:
#     TOPOLOGY_FILE / FLOW_FILE / CBAP_LINK_FILE / CBAP_PATH_FILE
# e.g. "FLOW_FILE ckpt_cbap_s3_out/s3_flow.txt", a path that does not exist.
# All 12 cells would have failed to read their topology and traffic.  Caught by
# the manifest's shared-parameter identity check before any cell was run.
#
# FIX: an explicit allow-list of OUTPUT keys.  Input keys are never touched.
# Nothing else changes: derived from the frozen s{1..6}_config.txt, only output
# paths plus the algorithm/controller fields differ.
set -u
cd /workspaces/yunxiao/simulation/experiment/scheme1_sba || exit 2

# Keys that name an INPUT the simulator must READ -- never rewritten.
INPUT_KEYS='TOPOLOGY_FILE|FLOW_FILE|CBAP_LINK_FILE|CBAP_PATH_FILE|ROUND_SCHEDULE_FILE|CBAP_FLOW_FILE'

QC_SOFT=0.5; QC_BOOST=0.30; QC_HGUARD=175; QC_HARD=838.86; QC_MSAFE=67072

for s in 1 2 3 4 5 6; do
  base="s${s}_config.txt"
  [ -f "$base" ] || { echo "MISSING $base"; exit 2; }

  for a in cbap dcqcn; do
    out="ckpt2_${a}_s${s}_out"
    cfg="ckpt2_${a}_s${s}.txt"
    rm -rf "$out"; mkdir -p "$out"

    # Rewrite ONLY output-bearing keys: any *_FILE that is not an input key,
    # plus the handful of *_OUTPUT_FILE names.  Preserve the basename.
    awk -v o="$out" -v ik="$INPUT_KEYS" '
      {
        if ($1 ~ /_FILE$/ && $1 !~ ("^(" ik ")$") && NF >= 2) {
          n = split($2, parts, "/")
          print $1 " " o "/" parts[n]
          next
        }
        print
      }' "$base" > "$cfg"

    if [ "$a" = "cbap" ]; then
      CCM=30; CBE=1; QCE=1
    else
      CCM=1;  CBE=0; QCE=0
    fi

    for kv in "CC_MODE $CCM" "CBAP_ENABLE $CBE" \
              "CBAP_QUEUE_CONTROLLER_ENABLE $QCE" \
              "CBAP_QC_SOFT_FRACTION $QC_SOFT" \
              "CBAP_QC_MAX_BOOST_RATIO $QC_BOOST" \
              "CBAP_QC_H_GUARD_US $QC_HGUARD" \
              "CBAP_QC_APP_HARD_DELAY_US $QC_HARD" \
              "CBAP_QC_SAFETY_MARGIN_BYTES $QC_MSAFE" \
              "CBAP_QC_TRACE_FILE ${out}/qc_trace.csv" \
              "CBAP_DELAY_CREDIT_ENABLE 0"; do
      k=${kv%% *}
      if grep -q "^${k}[[:space:]]" "$cfg"; then
        sed -i "s#^${k}[[:space:]].*#${kv}#" "$cfg"
      else
        echo "$kv" >> "$cfg"
      fi
    done
    echo "built $cfg -> $out"
  done
done

echo ""
echo "=== VERIFY: input keys point at REAL existing files ==="
BAD=0
for s in 1 2 3 4 5 6; do
  for a in cbap dcqcn; do
    c="ckpt2_${a}_s${s}.txt"
    for k in TOPOLOGY_FILE FLOW_FILE CBAP_LINK_FILE CBAP_PATH_FILE; do
      v=$(grep -m1 "^$k " "$c" | awk '{print $2}')
      [ -z "$v" ] && continue
      if [ ! -f "$v" ]; then echo "  MISSING INPUT $c: $k -> $v"; BAD=$((BAD+1)); fi
    done
  done
done
echo "  missing inputs: $BAD"

echo ""
echo "=== VERIFY: shared params identical across the CBAP/DCQCN pair ==="
EQBAD=0
for s in 1 2 3 4 5 6; do
  a="ckpt2_cbap_s${s}.txt"; b="ckpt2_dcqcn_s${s}.txt"
  for k in TOPOLOGY_FILE FLOW_FILE CBAP_LINK_FILE CBAP_PATH_FILE SIM_SEED \
           SIMULATOR_STOP_TIME QLEN_MON_START QLEN_MON_END APP_RATE_CAP_BPS \
           KMIN KMAX PMAX PAUSE_TIME BUFFER_SIZE ENABLE_QCN PACKET_PAYLOAD_SIZE; do
    va=$(grep -m1 "^$k " "$a" | awk '{print $2}')
    vb=$(grep -m1 "^$k " "$b" | awk '{print $2}')
    if [ "$va" != "$vb" ]; then echo "  s${s} $k: $va vs $vb"; EQBAD=$((EQBAD+1)); fi
  done
done
echo "  shared-param mismatches: $EQBAD"

echo ""
echo "=== VERIFY: pair differs only in algorithm/controller fields ==="
ALLOWED='CC_MODE|CBAP_ENABLE|CBAP_QUEUE_CONTROLLER_ENABLE'
DBAD=0
for s in 1 2 3 4 5 6; do
  a="ckpt2_cbap_s${s}.txt"; b="ckpt2_dcqcn_s${s}.txt"
  d=$(diff <(sed "s#ckpt2_cbap_s${s}_out#OUT#g" "$a") \
           <(sed "s#ckpt2_dcqcn_s${s}_out#OUT#g" "$b") \
      | grep -E '^[<>]' | awk '{print $1}' | wc -l)
  keys=$(diff <(sed "s#ckpt2_cbap_s${s}_out#OUT#g" "$a") \
              <(sed "s#ckpt2_dcqcn_s${s}_out#OUT#g" "$b") \
         | grep -E '^[<>]' | awk '{print $2}' | sort -u)
  bad=$(echo "$keys" | grep -vE "^($ALLOWED)$" | grep -v '^$' || true)
  if [ -n "$bad" ]; then echo "  s${s}: unexpected $(echo $bad|tr '\n' ' ')"; DBAD=$((DBAD+1));
  else echo "  s${s}: OK (only $(echo $keys|tr '\n' ' '))"; fi
done

echo ""
echo "=== VERIFY: no cell writes into another cell's directory ==="
LEAK=0
for s in 1 2 3 4 5 6; do
  for a in cbap dcqcn; do
    c="ckpt2_${a}_s${s}.txt"
    x=$(grep -oE 'ckpt2_[a-z]+_s[0-9]+_out' "$c" | sort -u | grep -v "^ckpt2_${a}_s${s}_out$" || true)
    [ -n "$x" ] && { echo "  LEAK $c: $x"; LEAK=$((LEAK+1)); }
  done
done
echo "  leaks: $LEAK"

echo ""
[ "$BAD" -eq 0 ] && [ "$EQBAD" -eq 0 ] && [ "$DBAD" -eq 0 ] && [ "$LEAK" -eq 0 ] \
  && echo "ALL CHECKS PASS" || { echo "CHECKS FAILED"; exit 3; }
