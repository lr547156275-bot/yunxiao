#!/bin/bash
set -u
cd /work/simulation/experiment/scheme1_sba || exit 2
L=CHECKPOINT_PROVENANCE/CKPT4_S3_LOG.txt
: > "$L"
for a in cbap dcqcn; do
  echo "### ckpt4_${a}_s3 start $(date -u '+%H:%M:%S') ###" | tee -a "$L"
  LD_LIBRARY_PATH=/work/simulation/build /work/simulation/build/scratch/third \
    ckpt4_${a}_s3.txt > ckpt4_${a}_s3_out/run.log 2>&1
  echo "ckpt4_${a}_s3 exit=$? wall_done=$(date -u '+%H:%M:%S')" | tee -a "$L"
done
echo "CKPT4_S3_PAIR_DONE" | tee -a "$L"
