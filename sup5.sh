#!/bin/bash
set -u
cd /work/simulation/experiment/scheme1_sba || exit 2
S=CHECKPOINT_PROVENANCE/SUPERVISOR5_LOG.txt
say(){ echo "[$(date -u '+%H:%M:%S')] $*" >> "$S"; }
say "sup5 start pid=$$"
for i in $(seq 1 300); do
  grep -q CKPT4_CBAP_S3_TRACE_DONE CHECKPOINT_PROVENANCE/CKPT4_S3_LOG.txt 2>/dev/null && { say "done"; exit 0; }
  pgrep -f rerun_cbap_s3 >/dev/null 2>&1 || { say "relaunch"; nohup bash /work/rerun_cbap_s3.sh >> /tmp/rr.txt 2>&1 & sleep 15; }
  sleep 60
done
