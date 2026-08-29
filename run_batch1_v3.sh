#!/bin/bash
# Batch 1 v3: S1/S2/S3/S6 x {CBAP, DCQCN}, serial MAX_JOBS=1.
# Acceptance delegated to accept_cell.sh (algorithm-aware contract, 3-state
# gates).  Resumes: a cell with a complete flow_summary under THIS binary is
# re-accepted, not re-run.
set -u
cd /work/simulation/experiment/scheme1_sba || exit 2

LOG=CHECKPOINT_PROVENANCE/BATCH1_V3_LOG.txt
: > "$LOG"
say() { echo "$*" | tee -a "$LOG"; }
avail() { local v; v=$(df -B1 /work 2>/dev/null | tail -1 | awk '{printf "%.2f", $4/1024/1024/1024}'); [ -n "$v" ] || v=0; echo "$v"; }
BINSHA=$(sha256sum /work/simulation/build/scratch/third | cut -d' ' -f1)

MIN_GUARD=2.5; NEXT_OUT=0.25; MARGIN=0.5
NEED=$(echo "$MIN_GUARD $NEXT_OUT $MARGIN" | awk '{printf "%.2f", $1+$2+$3}')

ORDER="cbap_s1 dcqcn_s1 cbap_s2 dcqcn_s2 cbap_s3 dcqcn_s3 cbap_s6 dcqcn_s6"
OK=0

for cell in $ORDER; do
  cfg="ckpt3_${cell}.txt"; out="ckpt3_${cell}_out"
  algo="${cell%%_*}"
  A=$(avail)
  say ""
  say "############ CELL $cell   avail=${A} GB need=${NEED} GB ############"
  if awk -v a="$A" -v n="$NEED" 'BEGIN{exit !(a<n)}'; then
    say "STOP: insufficient disk"; exit 4
  fi

  reuse=0
  if [ -s "$out/flow_summary.csv" ] && [ -f "$out/.binary" ] && \
     [ "$(cat "$out/.binary" 2>/dev/null)" = "$BINSHA" ]; then
    reuse=1
  fi
  # dcqcn_s1 and cbap_s1 already ran under this binary; mark them
  if [ -s "$out/flow_summary.csv" ] && [ ! -f "$out/.binary" ]; then
    L=$(wc -l < "$out/flow_summary.csv")
    if [ "$L" -gt 1 ]; then echo "$BINSHA" > "$out/.binary"; reuse=1; fi
  fi

  if [ "$reuse" = "1" ]; then
    say "  REUSE existing output (binary matches); re-accepting only"
  else
    rm -rf "$out"; mkdir -p "$out"
    T0=$(date +%s)
    say "  start=$(date -u '+%Y-%m-%dT%H:%M:%SZ') binary=${BINSHA:0:16}"
    LD_LIBRARY_PATH=/work/simulation/build /work/simulation/build/scratch/third "$cfg" > "$out/run.log" 2>&1
    RC=$?
    T1=$(date +%s)
    say "  exit=$RC wall=$((T1-T0))s size=$(du -sh "$out"|cut -f1) avail_after=$(avail) GB"
    [ "$RC" = "0" ] || { say "STOP: simulator exit $RC"; tail -4 "$out/run.log" | tee -a "$LOG"; exit 7; }
    echo "$BINSHA" > "$out/.binary"
  fi

  bash /work/accept_cell.sh "$out" "$algo" "$cfg" "$cell" 2>&1 | tee -a "$LOG"
  AR=${PIPESTATUS[0]}
  if [ "$AR" != "0" ]; then
    say "STOP: acceptance FAILED for $cell (applicable gate failure)"
    exit 8
  fi
  OK=$((OK+1))
  say "  CELL $cell ACCEPTED  ($OK/8)"
done

say ""
say "BATCH 1 COMPLETE: $OK/8 cells accepted"
