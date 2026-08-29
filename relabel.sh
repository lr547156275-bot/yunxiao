#!/bin/bash
# Relabel ckpt3: the arm disables the WHOLE capacity-reallocation mechanism, not
# just nonlinear migration.  All three keys are absent -> defaults:
#   cbap_migration_enable=false, cbap_core_initial_release=0,
#   cbap_initial_release_ratio=0.0
# Write-only: no config, result, log, SHA or checker is touched; nothing re-run.
set -u
cd /work/simulation/experiment/scheme1_sba || exit 2
STAMP=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
BIN=$(sha256sum /work/simulation/build/scratch/third | cut -d' ' -f1)
for s in 1 2 3 4 5 6; do for a in cbap dcqcn; do
  d="ckpt3_${a}_s${s}_out"; [ -d "$d" ] || continue
  [ -f "$d/ARM.txt" ] && cp -p "$d/ARM.txt" "$d/ARM.superseded_MIGRATION_OFF.txt"
  cat > "$d/ARM.txt" <<EOF
ARM=ABLATION_CAPACITY_REALLOCATION_OFF
ALSO_KNOWN_AS=FULL_REALLOCATION_OFF
SUPERSEDES_LABEL=ABLATION_MIGRATION_OFF (too narrow; see below)
SCENARIO=s${s}
ALGORITHM=${a}
LABELLED_AT=$STAMP
BINARY_SHA=$BIN

WHY "MIGRATION_OFF" WAS TOO NARROW
  s${s}_config.txt sets NONE of the three keys, so ALL of these are off:
      cbap_migration_enable      = false  (third.cc:195)   nonlinear migration
      cbap_core_initial_release  = 0      (third.cc:199)   core handover
      cbap_initial_release_ratio = 0.0    (third.cc:200)   rho / initial release
  So this arm measures the entire CAPACITY REALLOCATION mechanism disabled --
  initial release AND the subsequent migration -- not merely migration.

MEASURED CONSEQUENCE
  incast flows hold the admission grant 12,046,755 bps for the whole transfer.
  1 MiB / 12.05 Mbps = 0.696 s ~= measured 0.729 s.  CBAP_MIG lines = 0.

VALID USE
  - full capacity-reallocation-off ablation
  - instrument / plumbing correctness evidence
NOT VALID FOR
  - the paper headline CBAP-SBA vs DCQCN comparison
  - any claim about nonlinear migration alone (initial release is also off, so
    the two effects are not separable in this arm)

SEPARATION REQUIRES
  ABLATION_NONLINEAR_MIGRATION_OFF: identical initial allocation, rho_init and
  initial release as the rho=0.90 main arm, with ONLY the post-allocation
  nonlinear migration/update disabled.  Not yet run.
EOF
  echo "  relabelled $d"
done; done
cat > CHECKPOINT_PROVENANCE/CKPT3_ARM_CLASSIFICATION.txt <<EOF
CKPT3 BATCH CLASSIFICATION (corrected)
labelled_at=$STAMP
binary_sha=$BIN

ARM = ABLATION_CAPACITY_REALLOCATION_OFF   (aka FULL_REALLOCATION_OFF)
PREVIOUS LABEL = ABLATION_MIGRATION_OFF  -- withdrawn as too narrow

ROOT CAUSE (investigated)
  s{1..6}_config.txt set none of CBAP_MIGRATION_ENABLE /
  CBAP_CORE_INITIAL_RELEASE / CBAP_INITIAL_RELEASE_RATIO, so third.cc defaults
  disable migration, core handover AND initial release (rho=0) together.
  Initial release and nonlinear migration are therefore NOT separable here.

CORRECTION ALREADY ON RECORD
  An earlier note claimed iii5_s3_* measured 59.39 ms.  WRONG:
  iii5_s3_on_out mean incast FCT = 729.399 ms, bit-identical per-flow FCTs to
  ckpt3_cbap_s3_out.  The 59 ms figures are rec2_s3_on_out (rho=0.90) and
  v2_s3_rho09875_out (rho=0.9875), both migration ENABLED.

WORKING POINTS ON RECORD
  reallocation ON,  rho=0.90     59.391 ms  rec2_s3_on_out       MAIN (pre-registered)
  reallocation ON,  rho=0.9875   59.340 ms  v2_s3_rho09875_out   AGGRESSIVE/SENSITIVITY
  reallocation OFF, rho=0        729.399 ms ckpt3_*, iii5_s3_on  ABLATION (this arm)

PRE-REGISTERED PLAN (not to be changed on the basis of results)
  MAIN      CBAP rho=0.90 migration ON  vs  DCQCN stock baseline, S1-S6,
            paired on topology/flow/path/PG/seed/buffer/ECN/PFC
            order: S3 pair smoke test first, then full S1-S6
  SENS      rho=0.9875 reported with incast FCT/p99/goodput, background
            FCT/goodput, queue mean/p95/p99/max, utilisation, ECN/PFC/drop/retx;
            explicitly test whether its gain comes from pushing background to
            MIN_RATE
  ABLATION1 ABLATION_CAPACITY_REALLOCATION_OFF  (this arm, done)
  ABLATION2 ABLATION_NONLINEAR_MIGRATION_OFF    (same initial release as MAIN,
            only post-allocation migration disabled; NOT yet run)

STATUS: current 8-cell batch continues unmodified; no re-run, no overwrite.
EOF
echo "  wrote CKPT3_ARM_CLASSIFICATION.txt"
