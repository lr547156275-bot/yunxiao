#!/bin/bash
# Build the 12 checkpoint cells: S1-S6 x {CBAP-SBA with controller, DCQCN}.
#
# Derived from the frozen s{1..6}_config.txt by changing ONLY:
#   - output paths      (so nothing is overwritten)
#   - CC_MODE / CBAP_ENABLE for the DCQCN arm
#   - the controller keys for the CBAP arm
# Topology, flow file, seed, stop time, MIN_RATE, rho, ECN/PFC thresholds,
# Q_abs/Q_low/Q_high/Q_red and MAX_BOOST are inherited untouched.
set -u
cd /workspaces/yunxiao/simulation/experiment/scheme1_sba || exit 2

# Controller settings identical to the validated S3 preflight.
QC_SOFT=0.5
QC_BOOST=0.30
QC_HGUARD=175
QC_HARD=838.86
QC_MSAFE=67072

for s in 1 2 3 4 5 6; do
  base="s${s}_config.txt"
  [ -f "$base" ] || { echo "MISSING $base"; exit 2; }

  # ---------- CBAP-SBA arm (controller ON) ----------
  out="ckpt_cbap_s${s}_out"
  cfg="ckpt_cbap_s${s}.txt"
  rm -rf "$out"; mkdir -p "$out"
  # redirect every output path to this cell's directory
  sed -E "s#(^[A-Z_]*(FILE|OUTPUT_FILE)[[:space:]]+)[^[:space:]]*/#\1${out}/#" \
      "$base" > "$cfg"
  # any output key that had no directory component: prefix it
  awk -v o="$out" '
    /_FILE[ \t]/ || /^TRACE_OUTPUT_FILE[ \t]/ {
      n=split($0,a,/[ \t]+/);
      if (a[2] !~ /\//) { print a[1] " " o "/" a[2]; next }
    }
    { print }' "$cfg" > "$cfg.tmp" && mv "$cfg.tmp" "$cfg"

  # controller keys: replace if present, else append
  for kv in "CBAP_QUEUE_CONTROLLER_ENABLE 1" \
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

  # ---------- DCQCN baseline arm ----------
  out2="ckpt_dcqcn_s${s}_out"
  cfg2="ckpt_dcqcn_s${s}.txt"
  rm -rf "$out2"; mkdir -p "$out2"
  sed -e "s#${out}/#${out2}/#g" "$cfg" > "$cfg2"
  sed -i -e 's#^CC_MODE[[:space:]].*#CC_MODE 1#' \
         -e 's#^CBAP_ENABLE[[:space:]].*#CBAP_ENABLE 0#' \
         -e 's#^CBAP_QUEUE_CONTROLLER_ENABLE[[:space:]].*#CBAP_QUEUE_CONTROLLER_ENABLE 0#' \
         "$cfg2"
  echo "built $cfg2 -> $out2"
done

echo ""
echo "=== verification: no cell writes into another cell's directory ==="
for s in 1 2 3 4 5 6; do
  for a in cbap dcqcn; do
    c="ckpt_${a}_s${s}.txt"
    bad=$(grep -oE '[a-zA-Z0-9_]+_out/' "$c" | sort -u | grep -v "ckpt_${a}_s${s}_out/" | head -3)
    if [ -n "$bad" ]; then echo "  LEAK in $c: $bad"; else echo "  OK $c"; fi
  done
done

echo ""
echo "=== frozen-parameter diff vs base (must show ONLY expected keys) ==="
diff <(grep -vE '_FILE|_out/|^CC_MODE|^CBAP_ENABLE|^CBAP_QC_|^CBAP_QUEUE_CONTROLLER_ENABLE|^CBAP_DELAY_CREDIT_ENABLE' s3_config.txt) \
     <(grep -vE '_FILE|_out/|^CC_MODE|^CBAP_ENABLE|^CBAP_QC_|^CBAP_QUEUE_CONTROLLER_ENABLE|^CBAP_DELAY_CREDIT_ENABLE' ckpt_cbap_s3.txt) \
  && echo "  s3 CBAP cell: all non-controller params identical to base"
