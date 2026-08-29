#!/bin/bash
# Step 2 of 3: DELETE the six exact paths.  No wildcards anywhere.
# Re-runs the safety gate immediately before each removal.
set -u
cd /workspaces/yunxiao/simulation/experiment/scheme1_sba || exit 2

D=CHECKPOINT_PROVENANCE
OBS=$D/obsolete_runs
BASE=/workspaces/yunxiao/simulation/experiment/scheme1_sba

# exact realpaths, enumerated literally -- no globbing
P1=$BASE/qc_s3_rho090_fix_out
P2=$BASE/qc_s3_rho090_fixC_out
P3=$BASE/rec_flag0_out
P4=$BASE/rec_s3_off_out
P5=$BASE/flag0_new_out
P6=$BASE/flag0_c_out

echo "=== PRE-DELETE GUARD ==="
for p in "$P1" "$P2" "$P3" "$P4" "$P5" "$P6"; do
  # must exist, be a real dir, not a symlink, and live directly under BASE
  [ -d "$p" ] || { echo "  SKIP absent: $p"; continue; }
  [ -L "$p" ] && { echo "  ABORT symlink: $p"; exit 3; }
  [ "$(dirname "$p")" = "$BASE" ] || { echo "  ABORT not child: $p"; exit 3; }
  case "$p" in
    "$BASE"|"$BASE/"|"$BASE/.."*) echo "  ABORT parent: $p"; exit 3;;
  esac
  # its preserved evidence must exist
  nm=$(basename "$p")
  [ -d "$OBS/$nm" ] || { echo "  ABORT no provenance for $nm"; exit 3; }
  echo "  OK $p (provenance: $OBS/$nm)"
done

# live assets must still be present and outside
for a in "$BASE/rec2_s3_on_out" "$BASE/v2_s3_rho09875_out" \
         "$BASE/tx_trace2/s3_rho090_tx.csv" \
         "$BASE/tx_trace2/s3_rho09875_tx.csv" \
         "$BASE/r1_gates_v4.py" "$BASE/independent_acceptance_v2.py" \
         "$BASE/independent_acceptance.py" \
         "$BASE/$D/checker_R1v4_FROZEN.txt"; do
  [ -e "$a" ] || { echo "  ABORT live asset missing: $a"; exit 3; }
done
echo "  live assets present"

BEFORE=$(df -B1 /workspaces | tail -1 | awk '{print $4}')
echo ""
echo "=== DISK BEFORE ==="
df -h /workspaces | tail -1

echo ""
echo "=== DELETING (6 exact paths) ==="
for p in "$P1" "$P2" "$P3" "$P4" "$P5" "$P6"; do
  [ -d "$p" ] || continue
  sz=$(du -sh "$p" | cut -f1)
  rm -rf -- "$p"
  if [ -d "$p" ]; then
    echo "  FAILED to remove $p"
  else
    echo "  removed $p ($sz)"
  fi
done

AFTER=$(df -B1 /workspaces | tail -1 | awk '{print $4}')
echo ""
echo "=== DISK AFTER ==="
df -h /workspaces | tail -1
echo "freed_bytes=$((AFTER-BEFORE))"
echo "freed_human=$(echo "$AFTER $BEFORE" | awk '{printf "%.2f GB", ($1-$2)/1024/1024/1024}')"

echo ""
echo "=== POST-DELETE VERIFICATION: live checkpoints intact ==="
for a in rec2_s3_on_out v2_s3_rho09875_out; do
  echo "  $a: $(ls -1 $a | wc -l) files, $(du -sh $a | cut -f1)"
done
sha256sum r1_gates_v4.py independent_acceptance.py \
          independent_acceptance_v2.py r1_gates_v4_selftest.py \
          ../../build/scratch/third \
          ../../build/libns3.18-point-to-point-debug.so \
          tx_trace2/s3_rho090_tx.csv tx_trace2/s3_rho09875_tx.csv
echo ""
echo "  preserved provenance: $(find $OBS -type f | wc -l) files, $(du -sh $OBS | cut -f1)"
