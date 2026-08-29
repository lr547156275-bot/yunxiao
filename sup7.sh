#!/bin/bash
set -u
S=/work/simulation/experiment/scheme1_sba/CHECKPOINT_PROVENANCE/SUP7_LOG.txt
say(){ echo "[$(date -u '+%H:%M:%S')] $*" >> "$S"; }
say "sup7 start"
for i in $(seq 1 500); do
  grep -q CT_ALL_DONE /tmp/ct.log 2>/dev/null && { say done; exit 0; }
  pgrep -f 'scratch/third' >/dev/null 2>&1 || { say relaunch; nohup bash /work/mk_ct.sh >> /tmp/ctr.txt 2>&1 & sleep 12; }
  sleep 45
done
