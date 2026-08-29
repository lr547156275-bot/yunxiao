#!/bin/bash
# Item 2: same-run diagnostic. ckpt4 CBAP S3 config + ACTUATION + TX recorder,
# same binary (290cb41f), same seed. Only trace keys added.
set -u
cd /work/simulation/experiment/scheme1_sba || exit 2
SRC=ckpt4_cbap_s3.txt
CFG=sr_cbap_s3.txt
OUT=sr_cbap_s3_out
rm -rf "$OUT"; mkdir -p "$OUT"
sed "s#ckpt4_cbap_s3_out#${OUT}#g" "$SRC" > "$CFG"
for kv in "CBAP_ACTUATION_FILE ${OUT}/actuation.csv" \
          "TX_SERIALIZATION_TRACE_FILE ${OUT}/tx_serialization.csv"; do
  k=${kv%% *}
  if grep -q "^${k}[[:space:]]" "$CFG"; then sed -i "s#^${k}[[:space:]].*#${kv}#" "$CFG"
  else echo "$kv" >> "$CFG"; fi
done
echo "--- diff vs ckpt4 (should be ONLY the two trace keys) ---"
diff <(sed "s#ckpt4_cbap_s3_out#OUT#g" "$SRC" | sort) \
     <(sed "s#${OUT}#OUT#g" "$CFG" | sort) | grep -E '^[<>]'
echo "--- binary ---"
sha256sum /work/simulation/build/scratch/third
echo "--- launch ---"
LD_LIBRARY_PATH=/work/simulation/build /work/simulation/build/scratch/third "$CFG" > "$OUT/run.log" 2>&1
echo "sr_cbap_s3 exit=$?"
echo SR_DONE
