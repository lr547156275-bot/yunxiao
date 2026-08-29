#!/bin/bash
set -u
cd /work/simulation/experiment/scheme1_sba || exit 2
SRC=ckpt4_dcqcn_s3.txt
CFG=sr_dcqcn_s3.txt
OUT=sr_dcqcn_s3_out
rm -rf "$OUT"; mkdir -p "$OUT"
sed "s#ckpt4_dcqcn_s3_out#${OUT}#g" "$SRC" > "$CFG"
k=TX_SERIALIZATION_TRACE_FILE
kv="$k ${OUT}/tx_serialization.csv"
if grep -q "^${k}[[:space:]]" "$CFG"; then sed -i "s#^${k}[[:space:]].*#${kv}#" "$CFG"
else echo "$kv" >> "$CFG"; fi
echo "--- diff vs ckpt4 dcqcn (should be ONLY the tx key) ---"
diff <(sed "s#ckpt4_dcqcn_s3_out#OUT#g" "$SRC" | sort) \
     <(sed "s#${OUT}#OUT#g" "$CFG" | sort) | grep -E '^[<>]'
LD_LIBRARY_PATH=/work/simulation/build /work/simulation/build/scratch/third "$CFG" > "$OUT/run.log" 2>&1
echo "sr_dcqcn_s3 exit=$?"
echo SRD_DONE
