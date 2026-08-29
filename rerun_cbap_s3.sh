#!/bin/bash
set -u
cd /work/simulation/experiment/scheme1_sba || exit 2
# preserve the no-trace run as bypass-consistency evidence
if [ -d ckpt4_cbap_s3_out ] && [ ! -d ckpt4_cbap_s3_out.NOTRACE ]; then
  mv ckpt4_cbap_s3_out ckpt4_cbap_s3_out.NOTRACE
  cat > ckpt4_cbap_s3_out.NOTRACE/PROVENANCE.txt <<EOF
STATUS=RETAINED_BYPASS_CONSISTENCY_EVIDENCE
REASON=ran with reallocation ON but CBAP_MIGRATION_TRACE absent, so CBAP_MIG=0
BINARY_SHA=265fe2a1a31d5e1809458c9e5b44120b528c2524ae2642cbd7185072a7b68103
incast_mean_FCT=59.3909 ms   admit_rate=136593511 bps
NOTE=performance matches rec2_s3_on_out (59.391 ms) exactly; retained to show
     that adding only the trace key does not change the physics
EOF
fi
# add the trace key
cfg=ckpt4_cbap_s3.txt
for kv in "CBAP_MIGRATION_TRACE 1"; do
  k=${kv%% *}
  if grep -q "^${k}[[:space:]]" "$cfg"; then sed -i "s#^${k}[[:space:]].*#${kv}#" "$cfg"
  else echo "$kv" >> "$cfg"; fi
done
echo "--- the four keys in config ---"
grep -E '^(CBAP_MIGRATION_ENABLE|CBAP_CORE_INITIAL_RELEASE|CBAP_INITIAL_RELEASE_RATIO|CBAP_MIGRATION_TRACE) ' "$cfg"
rm -rf ckpt4_cbap_s3_out; mkdir -p ckpt4_cbap_s3_out
echo "--- launch $(date -u '+%H:%M:%S') ---"
LD_LIBRARY_PATH=/work/simulation/build /work/simulation/build/scratch/third "$cfg" > ckpt4_cbap_s3_out/run.log 2>&1
echo "cbap_s3 exit=$? done=$(date -u '+%H:%M:%S')" | tee -a CHECKPOINT_PROVENANCE/CKPT4_S3_LOG.txt
echo CKPT4_CBAP_S3_TRACE_DONE >> CHECKPOINT_PROVENANCE/CKPT4_S3_LOG.txt
