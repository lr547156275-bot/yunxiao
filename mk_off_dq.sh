#!/bin/bash
set -u
cd /work/simulation/experiment/scheme1_sba || exit 2
OUT=ct_dcqcn_off_out; CFG=ct_dcqcn_off.txt
rm -rf "$OUT"; mkdir -p "$OUT"
sed "s#sr_dcqcn_s3_out#${OUT}#g" sr_dcqcn_s3.txt > "$CFG"
LD_LIBRARY_PATH=/work/simulation/build /work/simulation/build/scratch/third "$CFG" > "$OUT/run.log" 2>&1
echo "dcqcn_off exit=$?" >> /tmp/ct_par.log
echo DQ_OFF_DONE >> /tmp/ct_par.log
