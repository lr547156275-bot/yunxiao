#!/bin/bash
# Reclassify the ckpt3 batch as the MIGRATION-OFF ABLATION arm.
#
# Finding (investigated, not assumed): s3_config.txt -- and every
# s{1..6}_config.txt -- contains NONE of these three keys, so ckpt3 fell back to
# the third.cc defaults:
#     cbap_migration_enable      = false   (third.cc:195)
#     cbap_core_initial_release  = 0       (third.cc:199)
#     cbap_initial_release_ratio = 0.0     (third.cc:200)
# Consequence: incast flows keep the admission grant (12,046,755 bps) for the
# whole transfer.  1 MiB / 12.05 Mbps = 0.696 s, matching the measured 0.729 s.
# With migration ON (rho=0.90) the same scenario gives 59.39 ms -- a 12.3x
# difference that is a WORKING POINT difference, not a regression.
#
# Evidence that ckpt3 and iii5 are the same working point: their per-flow FCTs
# are bit-identical (0.729380525 / 0.729381024 for the first two incast flows).
#
# This script only writes labels.  No config, parameter, threshold, result or
# checker is modified.
set -u
cd /work/simulation/experiment/scheme1_sba || exit 2

STAMP=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
BIN=$(sha256sum /work/simulation/build/scratch/third | cut -d' ' -f1)

for s in 1 2 3 4 5 6; do
  for a in cbap dcqcn; do
    d="ckpt3_${a}_s${s}_out"
    [ -d "$d" ] || continue
    cat > "$d/ARM.txt" <<EOF
ARM=ABLATION_MIGRATION_OFF
SCENARIO=s${s}
ALGORITHM=${a}
LABELLED_AT=$STAMP
BINARY_SHA=$BIN

WHY THIS IS AN ABLATION, NOT THE MAIN ARM
  s${s}_config.txt does not set CBAP_MIGRATION_ENABLE,
  CBAP_CORE_INITIAL_RELEASE or CBAP_INITIAL_RELEASE_RATIO, so third.cc
  defaults apply:
      cbap_migration_enable      = false
      cbap_core_initial_release  = 0
      cbap_initial_release_ratio = 0.0   (rho = 0)
  The CBAP arm therefore runs admission + telemetry + queue controller but
  performs NO capacity handover.  CBAP_MIG lines in run.log = 0.

VALID USE
  - migration-off ablation baseline
  - instrument/plumbing correctness evidence
NOT VALID FOR
  - the paper's headline CBAP-SBA vs DCQCN comparison, which requires
    migration enabled with an explicit rho
COMPARE AGAINST
  rec2_s3_on_out        rho=0.90    mean incast FCT 59.391 ms
  v2_s3_rho09875_out    rho=0.9875  mean incast FCT 59.340 ms
  ckpt3_cbap_s3_out     rho=0 (off) mean incast FCT 729.399 ms
EOF
    echo "  labelled $d"
  done
done

# batch-level note next to the manifest
cat > CHECKPOINT_PROVENANCE/CKPT3_ARM_CLASSIFICATION.txt <<EOF
CKPT3 BATCH CLASSIFICATION
labelled_at=$STAMP
binary_sha=$BIN

ARM = ABLATION_MIGRATION_OFF

ROOT CAUSE (investigated)
  s{1..6}_config.txt set none of:
    CBAP_MIGRATION_ENABLE / CBAP_CORE_INITIAL_RELEASE /
    CBAP_INITIAL_RELEASE_RATIO
  -> third.cc defaults: migration=false, core_release=0, rho=0.0
  -> incast flows hold the admission grant 12,046,755 bps for the whole
     transfer; 1 MiB / 12.05 Mbps = 0.696 s ~= measured 0.729 s

CORRECTION TO AN EARLIER STATEMENT
  An earlier note claimed iii5_s3_* measured 59.39 ms.  That was WRONG.
  iii5_s3_on_out mean incast FCT = 729.399 ms (64/64 flows >= 0.1 s), and its
  per-flow FCTs are bit-identical to ckpt3_cbap_s3_out.  The 59 ms figures come
  from rec2_s3_on_out (rho=0.90) and v2_s3_rho09875_out (rho=0.9875), both with
  migration ENABLED.

WORKING POINTS ON RECORD
  migration ON,  rho=0.90     59.391 ms   rec2_s3_on_out
  migration ON,  rho=0.9875   59.340 ms   v2_s3_rho09875_out
  migration OFF, rho=0        729.399 ms  ckpt3_cbap_s3_out, iii5_s3_on_out

STATUS
  ckpt3 cells remain VALID as a migration-off ablation and as instrument
  correctness evidence.  They are NOT the main paper comparison arm.
  A migration-enabled paired batch is still required; its rho is a design
  decision and has not been chosen unilaterally.
EOF
echo "  wrote CHECKPOINT_PROVENANCE/CKPT3_ARM_CLASSIFICATION.txt"
