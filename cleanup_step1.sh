#!/bin/bash
# Step 1 of 3: SAFETY VERIFICATION + PROVENANCE PRESERVATION.
# Deletes NOTHING.  Refuses to proceed if any live asset is inside a target.
set -u
cd /workspaces/yunxiao/simulation/experiment/scheme1_sba || exit 2

D=CHECKPOINT_PROVENANCE
OBS=$D/obsolete_runs
mkdir -p "$OBS"

TARGETS="qc_s3_rho090_fix_out qc_s3_rho090_fixC_out rec_flag0_out rec_s3_off_out flag0_new_out flag0_c_out"

# ---- live assets that must NOT be inside any target ----------------------
LIVE="rec2_s3_on_out
v2_s3_rho09875_out
tx_trace2/s3_rho090_tx.csv
tx_trace2/s3_rho09875_tx.csv
r1_gates_v4.py
r1_gates_v4_selftest.py
independent_acceptance_v2.py
independent_acceptance.py
$D/checker_R1v4_FROZEN.txt
$D/V2_s3_rho090_FROZEN.txt
../../build/scratch/third
../../build/libns3.18-point-to-point-debug.so
../../scratch/tx-serialization-recorder.h
rec2_s3_on.txt
v2_s3_rho09875.txt"

echo "=== SAFETY CHECK: live assets must not be inside any delete target ==="
BAD=0
for a in $LIVE; do
  if [ ! -e "$a" ]; then
    echo "  MISSING LIVE ASSET: $a"
    BAD=$((BAD+1)); continue
  fi
  rp=$(realpath "$a")
  for t in $TARGETS; do
    [ -e "$t" ] || continue
    trp=$(realpath "$t")
    case "$rp" in
      "$trp"|"$trp"/*) echo "  CONFLICT: $a is inside $t"; BAD=$((BAD+1));;
    esac
  done
done
if [ "$BAD" -ne 0 ]; then
  echo "REFUSING TO PROCEED: $BAD problem(s)"
  exit 3
fi
echo "  OK: all $(echo "$LIVE" | wc -l) live assets verified outside targets"

# ---- targets must be plain dirs, not symlinks, not parents ---------------
echo ""
echo "=== TARGET VALIDATION ==="
for t in $TARGETS; do
  if [ ! -d "$t" ]; then echo "  SKIP (absent): $t"; continue; fi
  if [ -L "$t" ]; then echo "  REFUSE: $t is a symlink"; exit 3; fi
  case "$t" in
    */*|.|..|/*) echo "  REFUSE: $t not a direct child"; exit 3;;
  esac
  echo "  OK $t -> $(realpath "$t")"
done

# ---- manifest -----------------------------------------------------------
MAN=$D/CLEANUP_PROVENANCE_MANIFEST.txt
{
  echo "CLEANUP PROVENANCE MANIFEST"
  echo "generated_utc=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "git_head=$(cd /workspaces/yunxiao && git rev-parse HEAD)"
  echo ""
  echo "=== SHARED ASSET SHAs AT CLEANUP TIME ==="
  sha256sum ../../build/scratch/third \
            ../../build/libns3.18-point-to-point-debug.so \
            ../../scratch/tx-serialization-recorder.h \
            r1_gates_v4.py r1_gates_v4_selftest.py \
            independent_acceptance.py independent_acceptance_v2.py \
            s3_config.txt s3_flow.txt s3_cbap_link.txt s3_cbap_path.txt \
            2>/dev/null
  echo ""
  for t in $TARGETS; do
    [ -d "$t" ] || continue
    echo "=== TARGET: $t ==="
    echo "realpath   = $(realpath "$t")"
    echo "size       = $(du -sh "$t" | cut -f1)"
    if [ -f "$t/INVALID_REASON.txt" ]; then
      echo "status     = INVALID"
      sed 's/^/  /' "$t/INVALID_REASON.txt"
    elif [ -f "$t/SUPERSEDED.txt" ]; then
      echo "status     = SUPERSEDED"
      sed 's/^/  /' "$t/SUPERSEDED.txt"
    else
      echo "status     = SUPERSEDED (session intermediate)"
    fi
    case "$t" in
      qc_s3_rho090_fix_out)
        echo "reason     = defect A fixed but floor summed over steered set (6.7072 G)"
        echo "replaced_by= rec2_s3_on_out (S3 rho=0.90, TOP_LEVEL 20/20)";;
      qc_s3_rho090_fixC_out)
        echo "reason     = three sets correct but GC keyed on live => floor=0, DRAIN_MAX=1.0C"
        echo "replaced_by= rec2_s3_on_out (S3 rho=0.90, TOP_LEVEL 20/20)";;
      rec_flag0_out)
        echo "reason     = bypass evidence for the pre-signature-fix binary"
        echo "replaced_by= rec2_flag0_out (flag0 21/21 vs au_s3_rho090_out)";;
      rec_s3_off_out)
        echo "reason     = recorder-OFF evidence for the pre-signature-fix binary"
        echo "replaced_by= rec2_s3_off_out (ON vs OFF 13/13 bit-identical)";;
      flag0_new_out|flag0_c_out)
        echo "reason     = flag0 bit-identity evidence for an earlier binary"
        echo "replaced_by= rec2_flag0_out";;
    esac
    echo "files_kept_in_provenance:"
    for f in run.log flow_summary.csv controller_summary.csv admission.csv \
             INVALID_REASON.txt SUPERSEDED.txt port_summary.csv \
             round_summary.csv eta_feasibility.csv flow_plan.csv; do
      [ -f "$t/$f" ] && echo "  $OBS/$t/$f"
    done
    echo "files_discarded_large:"
    for f in qc_trace.csv pfc_ports.csv pfc_audit.csv \
             selected_flow_timeseries.csv selected_link_timeseries.csv \
             qlen.txt trace_output.txt; do
      [ -f "$t/$f" ] && echo "  $t/$f ($(du -sh "$t/$f" | cut -f1))"
    done
    echo ""
  done
  echo "=== PER-FILE SHA256 OF PRESERVED EVIDENCE ==="
} > "$MAN"

# ---- copy the small evidence -------------------------------------------
echo ""
echo "=== PRESERVING SMALL EVIDENCE ==="
for t in $TARGETS; do
  [ -d "$t" ] || continue
  mkdir -p "$OBS/$t"
  for f in run.log flow_summary.csv controller_summary.csv admission.csv \
           INVALID_REASON.txt SUPERSEDED.txt port_summary.csv \
           round_summary.csv eta_feasibility.csv flow_plan.csv \
           rate_transition.csv sba_events.csv increase_audit.csv \
           feedback_summary.csv group_round_summary.csv pfc_events.csv; do
    [ -f "$t/$f" ] && cp -p "$t/$f" "$OBS/$t/$f"
  done
  # the cell's own config, if identifiable
  cfg="${t%_out}.txt"
  [ -f "$cfg" ] && cp -p "$cfg" "$OBS/$t/CONFIG_$cfg"
  n=$(ls -1 "$OBS/$t" 2>/dev/null | wc -l)
  echo "  $t -> $OBS/$t ($n files, $(du -sh "$OBS/$t" | cut -f1))"
done

find "$OBS" -type f -exec sha256sum {} \; | sort -k2 >> "$MAN"
echo ""
echo "=== MANIFEST ==="
wc -l "$MAN"
echo ""
echo "=== DISK BEFORE ==="
df -h /workspaces | tail -1
du -shc $TARGETS 2>/dev/null | tail -1
echo ""
echo "STEP 1 COMPLETE -- nothing deleted."
