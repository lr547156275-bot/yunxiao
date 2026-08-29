#!/bin/bash
# serial supervisor: cbap then dcqcn, survives VM restarts
set -u
cd /work/simulation/experiment/scheme1_sba || exit 2
S=CHECKPOINT_PROVENANCE/SUP6_LOG.txt
say(){ echo "[$(date -u '+%H:%M:%S')] $*" >> "$S"; }
say "sup6 start pid=$$"
for i in $(seq 1 400); do
  cdone=0; ddone=0
  grep -q SR_DONE /tmp/sr.txt 2>/dev/null && cdone=1
  grep -q SRD_DONE /tmp/srd.txt 2>/dev/null && ddone=1
  if [ "$cdone" = "1" ] && [ "$ddone" = "1" ]; then say "both done"; exit 0; fi
  if ! pgrep -f 'scratch/third' >/dev/null 2>&1; then
    if [ "$cdone" = "0" ]; then
      say "relaunch cbap"; nohup bash /work/mk_sr.sh > /tmp/sr.txt 2>&1 & sleep 12
    else
      say "relaunch dcqcn"; nohup bash /work/mk_srd.sh > /tmp/srd.txt 2>&1 & sleep 12
    fi
  fi
  sleep 45
done
