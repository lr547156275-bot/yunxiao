#!/bin/bash
# Round-2 cleanup: reclaim ONLY intermediate outputs that are (a) explicitly
# labelled INVALID_* / SUPERSEDED_*, or (b) instrument-verification runs whose
# conclusion + SHA are already archived and which have a valid replacement.
#
# Minimal evidence is copied to CHECKPOINT_PROVENANCE/obsolete_runs2/ BEFORE any
# deletion: run.log, flow_summary, controller_summary, admission, port_summary,
# round_summary, rate_transition, plus the cell config and a SHA manifest.
#
# No formal experiment result is touched.  Deletion is by explicit path only --
# no wildcards expand into the delete command.
set -u
cd /work/simulation/experiment/scheme1_sba || exit 2

D=CHECKPOINT_PROVENANCE
OBS=$D/obsolete_runs2
MAN=$D/CLEANUP2_MANIFEST.txt
mkdir -p "$OBS"

# Instrument-verification and superseded intermediates.  Every one of these has
# its verdict already recorded in CHECKPOINT_PROVENANCE and a live replacement.
T1=ml_flag0_out          # bypass evidence, superseded by iii4_flag0_out
T2=ml_s3_off_out         # S3 ON/OFF pre-decouple binary
T3=ml_s3_on_out
T4=ml_s6_off_out         # S6 ON/OFF pre-decouple binary
T5=ml_s6_on_out
T6=rec2_flag0_out        # older flag0 evidence (pre-multilink recorder)
T7=rec2_s3_off_out
T8=ckpt3_cbap_s1_out.PREFIX_BINARY_a6bd0124   # pre-decouple binary smoke run
T9=vd_flag0_out          # never completed (superseded by iii4)

TARGETS="$T1 $T2 $T3 $T4 $T5 $T6 $T7 $T8 $T9"

# Live assets that must NOT be inside any target.
LIVE="rec2_s3_on_out
v2_s3_rho09875_out
iii2_cbap_s6_out
iii2_dcqcn_s6_out
iii4_flag0_out
ckpt3_cbap_s1_out
ckpt3_dcqcn_s1_out
tx_ml/s3_on_tx.csv
tx_ml/s6_on_tx.csv
tx_trace2/s3_rho090_tx.csv
r1_gates_v4.py
r1_gates_ml_v2.py
independent_acceptance.py
independent_acceptance_v2.py
link_identity_validator.py
$D/RUN_MANIFEST_12CELL_v2.txt
$D/FREEZE_PRE_BATCH1.txt"

echo "=== SAFETY: live assets must not be inside any target ==="
BAD=0
for a in $LIVE; do
  [ -e "$a" ] || { echo "  MISSING LIVE: $a"; BAD=$((BAD+1)); continue; }
  rp=$(realpath "$a")
  for t in $TARGETS; do
    [ -e "$t" ] || continue
    trp=$(realpath "$t")
    case "$rp" in "$trp"|"$trp"/*) echo "  CONFLICT $a in $t"; BAD=$((BAD+1));; esac
  done
done
[ "$BAD" -eq 0 ] || { echo "REFUSING: $BAD problem(s)"; exit 3; }
echo "  OK $(echo "$LIVE" | wc -l) live assets verified outside targets"

echo ""
echo "=== PRESERVE minimal evidence ==="
{
  echo "CLEANUP2_MANIFEST"
  echo "utc=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "disk_before=$(df -h /work | tail -1 | awk '{print $4}')"
  echo ""
} > "$MAN"
for t in $TARGETS; do
  [ -d "$t" ] || { echo "  skip (absent) $t"; continue; }
  mkdir -p "$OBS/$t"
  for f in run.log flow_summary.csv controller_summary.csv admission.csv \
           port_summary.csv round_summary.csv rate_transition.csv \
           flow_plan.csv sba_events.csv pfc_events.csv \
           INVALID_REASON.txt SUPERSEDED.txt INVALID_LOW_DISK.txt; do
    [ -f "$t/$f" ] && cp -p "$t/$f" "$OBS/$t/$f"
  done
  cfg="${t%_out}.txt"
  [ -f "$cfg" ] && cp -p "$cfg" "$OBS/$t/CONFIG_$(basename "$cfg")"
  {
    echo "=== $t ==="
    echo "realpath=$(realpath "$t")"
    echo "size=$(du -sh "$t" | cut -f1)"
    case "$t" in
      ml_*)   echo "reason=instrument verification under pre-decouple binary a6bd0124"
              echo "replaced_by=iii2_*/iii4_*/iii5_* under binary 265fe2a1";;
      rec2_*) echo "reason=bypass evidence under the single-link recorder 54a11a1d"
              echo "replaced_by=iii4_flag0_out (multilink recorder 4b9a4098)";;
      ckpt3_cbap_s1_out.PREFIX*) echo "reason=SUPERSEDED_PRE_DECOUPLE_BINARY smoke run"
              echo "replaced_by=ckpt3_cbap_s1_out under binary 265fe2a1";;
      vd_*)   echo "reason=aborted verification attempt, never completed"
              echo "replaced_by=iii4_flag0_out";;
    esac
    echo "evidence_kept=$OBS/$t ($(ls -1 "$OBS/$t" 2>/dev/null | wc -l) files)"
    echo ""
  } >> "$MAN"
  echo "  $t -> $OBS/$t ($(ls -1 "$OBS/$t" | wc -l) files)"
done
find "$OBS" -type f -exec sha256sum {} \; | sort -k2 >> "$MAN"

BEFORE=$(df -B1 /work | tail -1 | awk '{print $4}')
echo ""
echo "=== DELETE (explicit paths only) ==="
for p in "$T1" "$T2" "$T3" "$T4" "$T5" "$T6" "$T7" "$T8" "$T9"; do
  [ -d "$p" ] || continue
  [ -L "$p" ] && { echo "  ABORT symlink $p"; exit 3; }
  [ -d "$OBS/$p" ] || { echo "  ABORT no provenance for $p"; exit 3; }
  sz=$(du -sh "$p" | cut -f1)
  rm -rf -- "$p"
  [ -d "$p" ] && echo "  FAILED $p" || echo "  removed $p ($sz)"
done
AFTER=$(df -B1 /work | tail -1 | awk '{print $4}')

echo ""
echo "=== RESULT ==="
df -h /work | tail -1
echo "freed=$(echo "$AFTER $BEFORE" | awk '{printf "%.2f GB", ($1-$2)/1024/1024/1024}')"
echo "available=$(df -B1 /work | tail -1 | awk '{printf "%.2f GB", $4/1024/1024/1024}')"
echo "provenance=$(find "$OBS" -type f | wc -l) files, $(du -sh "$OBS" | cut -f1)"
echo "disk_after=$(df -h /work | tail -1 | awk '{print $4}')" >> "$MAN"
echo ""
echo "=== live checkpoints intact ==="
for d in iii2_cbap_s6_out iii2_dcqcn_s6_out iii4_flag0_out rec2_s3_on_out v2_s3_rho09875_out; do
  [ -d "$d" ] && echo "  $d: $(ls -1 "$d" | wc -l) files $(du -sh "$d" | cut -f1)"
done
