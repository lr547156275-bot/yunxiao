#!/bin/bash
set -u
cd /work/simulation/experiment/scheme1_sba || exit 2
S=CHECKPOINT_PROVENANCE/SUPERVISOR4_LOG.txt
say(){ echo "[$(date -u '+%H:%M:%S')] $*" >> "$S"; }
say "supervisor4 start pid=$$"
for i in $(seq 1 300); do
  grep -q CKPT4_S3_PAIR_DONE CHECKPOINT_PROVENANCE/CKPT4_S3_LOG.txt 2>/dev/null && { say "pair done"; exit 0; }
  if ! pgrep -f run_ckpt4_s3 >/dev/null 2>&1; then
    say "runner absent -- relaunching"
    nohup bash /work/run_ckpt4_s3.sh >> /tmp/ck4.txt 2>&1 &
    sleep 15
  fi
  sleep 60
done
