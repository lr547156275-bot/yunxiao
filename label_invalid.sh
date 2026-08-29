#!/bin/bash
# Section 3: label old results with the SPECIFIC reason they are invalid.
#
# Writes a marker file INSIDE each directory.  Nothing is renamed, moved,
# overwritten or deleted -- the raw traces stay exactly where they are so they
# remain citable as provenance.
set -u
cd /workspaces/yunxiao/simulation/experiment/scheme1_sba || exit 2

mark() {
  d="$1"; reason="$2"; detail="$3"
  [ -d "$d" ] || return 0
  # never clobber an existing marker
  if [ -f "$d/INVALID_REASON.txt" ]; then
    echo "  SKIP (already marked) $d"
    return 0
  fi
  {
    echo "STATUS=INVALID"
    echo "REASON=$reason"
    echo "DETAIL=$detail"
    echo "LABELLED_AT_COMMIT=a745d58dec82ffa445155557147b0bba42d0dee6"
    echo "RETAINED=yes  # raw trace kept for provenance; do not delete"
    echo "USABLE_FOR_PAPER=no"
  } > "$d/INVALID_REASON.txt"
  echo "  marked $d -> $reason"
}

echo "=== controller-era runs with wire-accounting defect (1064 as ratio) ==="
# qc_trace has 24 columns => pre-defect-C telemetry, floor built on 1064.
mark qc_s3_rho090_out INVALID_WIRE_ACCOUNTING \
  "floor_wire=6.916G from 1064/1000 ratio; also control-scope defect present"
mark qc_s3_rho09875_out INVALID_WIRE_ACCOUNTING \
  "17-column trace, pre-fix controller; 1064 ratio in floor"
mark qc_s3_rho090_out.INVALID_WIRE_ACCOUNTING_AND_CONTROL_SCOPE \
  INVALID_WIRE_ACCOUNTING \
  "duplicate of qc_s3_rho090_out kept as provenance copy"

echo "=== runs with control-scope defect (qcOwnsRates = !ledger.empty()) ==="
mark qc_s3_rho090_fix_out INVALID_CONTROL_SCOPE \
  "defect A fixed, but floor summed over steered set: 6.7072G, DRAIN_MAX->1.0C"

echo "=== runs with floor-membership defect (floor set == steered set) ==="
mark qc_s3_rho090_fixC_out INVALID_FLOOR_MEMBERSHIP \
  "three sets built correctly but GC keyed on live => bg entry erased, floor=0"

echo "=== superseded flag=0 baselines (kept as evidence, not invalid) ==="
for d in flag0_new_out flag0_c_out; do
  [ -d "$d" ] || continue
  if [ -f "$d/SUPERSEDED.txt" ]; then echo "  SKIP $d"; continue; fi
  {
    echo "STATUS=SUPERSEDED_EVIDENCE"
    echo "REASON=flag0 bit-identity evidence for an earlier binary"
    echo "RETAINED=yes"
  } > "$d/SUPERSEDED.txt"
  echo "  marked $d -> SUPERSEDED_EVIDENCE"
done

echo ""
echo "=== pg=0 scan across ALL retained result dirs ==="
# Hard gate: zero pg=0 rows may be used as formal data.  Scan the flow files
# each run actually consumed, not the current ones.
pg0=0
for d in *_out *_out.*; do
  [ -d "$d" ] || continue
  f="$d/flow_summary.csv"
  [ -f "$f" ] || continue
  # flow_summary has no pg column; the authoritative pg is in the config's
  # FLOW_FILE.  Record which dirs predate the pg=3 correction by checking for
  # the legacy marker left by the earlier round.
  if [ -f "$d/pg0_invalid" ] || [ -f "$d/PG0_INVALID.txt" ]; then
    pg0=$((pg0+1))
    echo "  pg0-era: $d"
  fi
done
echo "  dirs carrying an explicit pg0 marker: $pg0"
echo ""
echo "=== current flow files: pg distribution (must all be 3) ==="
for f in s1_flow.txt s2_flow.txt s3_flow.txt s4_flow.txt s5_flow.txt s6_flow.txt; do
  printf '  %-14s ' "$f"
  awk 'NR>1{c[$3]++} END{for(p in c) printf "pg=%s:%d ", p, c[p]; print ""}' "$f"
done
