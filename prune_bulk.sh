#!/bin/bash
# Reclaim disk by deleting ONLY bulk trace files inside experiment output
# directories.  Writes a full manifest before deleting anything.
#
# SAFETY, by construction:
#   * operates only on paths matching /work/simulation/experiment/scheme1_sba/*_out/
#   * only filenames on an explicit bulk whitelist, and only if > 2 MB
#   * never touches source, scratch, build, .git, *.txt configs, flow/link/path/
#     schedule inputs, CHECKPOINT_PROVENANCE, analysis bundles, or matrix_logs
#   * PROTECTED result dirs keep their traces intact (still needed for the
#     current comparison and the pending Pareto sweep)
#   * every summary CSV is kept everywhere, so the scientific record survives
set -u
BASE=/work/simulation/experiment/scheme1_sba
MAN=/work/CHECKPOINT_PROVENANCE/PRUNE_MANIFEST.txt

# Dirs whose traces are still required
PROTECT="mb_off_out mb_phase_out mb_both_out mb_snap_out
         sr_cbap_s3_out sr_dcqcn_s3_out gs_s3_on_out
         v3_split_out v4_off_out v4_on_out"

# Bulk trace filenames (large, regenerable, not summary results)
BULK="selected_link_timeseries.csv selected_flow_timeseries.csv qlen.txt
      qc_trace.csv pfc_ports.csv pfc_audit.csv tx_serialization.csv
      gap_snapshot.csv delay_credit.csv trace_output.txt sender_opp.csv
      causal_queue.csv causal_pacer.csv"

cd "$BASE" || { echo "BASE missing"; exit 1; }
: > "$MAN"
{
  echo "PRUNE_MANIFEST $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "rule: only *_out/<bulk-name> files larger than 2 MB"
  echo "protected dirs (traces kept): $(echo $PROTECT | tr -s ' ')"
  echo "df before:"; df -h /work | tail -1
  echo ""
} >> "$MAN"

total=0; count=0; skipped=0
for d in *_out; do
  [ -d "$d" ] || continue
  prot=0
  for p in $PROTECT; do [ "$d" = "$p" ] && prot=1; done
  if [ "$prot" -eq 1 ]; then
    echo "PROTECTED  $d" >> "$MAN"; skipped=$((skipped+1)); continue
  fi
  for f in $BULK; do
    t="$d/$f"
    [ -f "$t" ] || continue
    sz=$(stat -c%s "$t")
    [ "$sz" -le 2097152 ] && continue          # keep anything small
    printf 'DELETE  %10d  %s  %s\n' "$sz" "$(stat -c%y "$t" | cut -d. -f1)" "$t" >> "$MAN"
    total=$((total+sz)); count=$((count+1))
  done
done

{
  echo ""
  echo "files_to_delete=$count"
  echo "bytes_to_delete=$total"
  printf 'projected_reclaim=%.2f GB\n' "$(echo "$total" | awk '{print $1/1073741824}')"
  echo "protected_dirs=$skipped"
} >> "$MAN"

printf 'manifest: %s\nfiles=%d  reclaim=%.2f GB  protected=%d\n' \
  "$MAN" "$count" "$(echo "$total" | awk '{print $1/1073741824}')" "$skipped"

# ---- delete, one exact path at a time, re-checking every guard ------------
del=0; freed=0
while IFS= read -r line; do
  case "$line" in DELETE*) ;; *) continue;; esac
  t=$(echo "$line" | awk '{print $NF}')
  case "$t" in
    *_out/*) : ;;
    *) echo "REFUSE not in an _out dir: $t"; continue;;
  esac
  case "$t" in
    *src/*|*scratch/*|*build/*|*.git/*|*CHECKPOINT*|*analysis/*|*.txt)
      echo "REFUSE protected pattern: $t"; continue;;
  esac
  base=$(basename "$t"); ok=0
  for f in $BULK; do [ "$base" = "$f" ] && ok=1; done
  [ "$ok" -eq 1 ] || { echo "REFUSE not on bulk list: $t"; continue; }
  [ -f "$BASE/$t" ] || continue
  sz=$(stat -c%s "$BASE/$t")
  rm -f -- "$BASE/$t"
  if [ -f "$BASE/$t" ]; then echo "FAILED $t"; else del=$((del+1)); freed=$((freed+sz)); fi
done < "$MAN"

{
  echo ""
  echo "deleted_files=$del"
  printf 'freed=%.2f GB\n' "$(echo "$freed" | awk '{print $1/1073741824}')"
  echo "df after:"; df -h /work | tail -1
} >> "$MAN"

printf 'deleted=%d  freed=%.2f GB\n' "$del" "$(echo "$freed" | awk '{print $1/1073741824}')"
df -h /work | tail -1

echo "--- integrity: source and inputs untouched ---"
du -sm /work/simulation/src /work/simulation/scratch /work/simulation/build \
       /work/CHECKPOINT_PROVENANCE 2>/dev/null
echo "config/input files still present:"
ls "$BASE"/*.txt 2>/dev/null | wc -l
echo "summary CSVs still present across all _out dirs:"
find "$BASE" -maxdepth 2 -name flow_summary.csv | wc -l
echo "--- protected dirs intact ---"
for p in $PROTECT; do
  [ -d "$BASE/$p" ] && printf '  %-18s %sMB\n' "$p" "$(du -sm "$BASE/$p" | cut -f1)"
done
