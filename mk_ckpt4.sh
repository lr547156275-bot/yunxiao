#!/bin/bash
# 1) Relabel ckpt3 -> ABLATION_FULL_CAPACITY_REALLOCATION_OFF (write-only)
# 2) Generate ckpt4 S3 pair: CBAP rho=0.90 migration ON, vs DCQCN baseline
# Inherits the frozen config; only the three reallocation keys are added.
set -u
cd /work/simulation/experiment/scheme1_sba || exit 2
STAMP=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
BIN=$(sha256sum /work/simulation/build/scratch/third | cut -d' ' -f1)

echo "=== 1) relabel ckpt3 ==="
for s in 1 2 3 4 5 6; do for a in cbap dcqcn; do
  d="ckpt3_${a}_s${s}_out"; [ -d "$d" ] || continue
  sed -i 's/^ARM=.*/ARM=ABLATION_FULL_CAPACITY_REALLOCATION_OFF/' "$d/ARM.txt" 2>/dev/null
  grep -q 'NOT_A_CBAP_MAIN_RESULT' "$d/ARM.txt" 2>/dev/null || cat >> "$d/ARM.txt" <<EOF

NOT_A_CBAP_MAIN_RESULT=true
NOT_A_MIGRATION_ONLY_ABLATION=true
  All THREE keys were off (MIGRATION_ENABLE, CORE_INITIAL_RELEASE,
  INITIAL_RELEASE_RATIO), so initial release and nonlinear migration cannot be
  separated here.  Must not be presented as "the CBAP result" nor as a
  migration-only ablation.
RELABELLED_AT=$STAMP
EOF
done; done
sed -i 's/^ARM = .*/ARM = ABLATION_FULL_CAPACITY_REALLOCATION_OFF/' \
  CHECKPOINT_PROVENANCE/CKPT3_ARM_CLASSIFICATION.txt 2>/dev/null
echo "  relabelled 12 dirs + batch classification"

echo "=== 2) generate ckpt4 S3 pair ==="
for a in cbap dcqcn; do
  src="ckpt3_${a}_s3.txt"
  out="ckpt4_${a}_s3_out"
  cfg="ckpt4_${a}_s3.txt"
  [ -f "$src" ] || { echo "MISSING $src"; exit 2; }
  rm -rf "$out"; mkdir -p "$out"
  sed "s#ckpt3_${a}_s3_out#${out}#g" "$src" > "$cfg"
  if [ "$a" = "cbap" ]; then
    for kv in "CBAP_MIGRATION_ENABLE 1" \
              "CBAP_CORE_INITIAL_RELEASE 1" \
              "CBAP_INITIAL_RELEASE_RATIO 0.90" \
              "CBAP_RATE_TRANSITION_FILE ${out}/rate_transition.csv"; do
      k=${kv%% *}
      if grep -q "^${k}[[:space:]]" "$cfg"; then
        sed -i "s#^${k}[[:space:]].*#${kv}#" "$cfg"
      else
        echo "$kv" >> "$cfg"
      fi
    done
  fi
  echo "  built $cfg -> $out"
done

echo "=== 3) audit: only the 3 keys differ from ckpt3 ==="
diff <(sed 's#ckpt3_cbap_s3_out#OUT#g' ckpt3_cbap_s3.txt | sort) \
     <(sed 's#ckpt4_cbap_s3_out#OUT#g' ckpt4_cbap_s3.txt | sort) \
  | grep -E '^[<>]' || echo "  (no diff?!)"
echo "=== 4) pair shares all inputs ==="
for k in TOPOLOGY_FILE FLOW_FILE ROUND_SCHEDULE_FILE CBAP_LINK_FILE CBAP_PATH_FILE \
         SIM_SEED SIMULATOR_STOP_TIME QLEN_MON_START QLEN_MON_END PACKET_PAYLOAD_SIZE \
         KMIN KMAX PMAX PAUSE_TIME BUFFER_SIZE ENABLE_QCN; do
  va=$(grep -m1 "^$k " ckpt4_cbap_s3.txt | awk '{print $2}')
  vb=$(grep -m1 "^$k " ckpt4_dcqcn_s3.txt | awk '{print $2}')
  [ "$va" = "$vb" ] || echo "  MISMATCH $k: $va vs $vb"
done
echo "  pair input check done"
echo "=== 5) frozen values unchanged ==="
grep -E '^(CBAP_QC_MAX_BOOST_RATIO|CBAP_QC_H_GUARD_US|CBAP_QC_APP_HARD_DELAY_US|CBAP_QC_SAFETY_MARGIN_BYTES|MIN_RATE|KMIN|KMAX)' ckpt4_cbap_s3.txt
echo "=== 6) the three keys as parsed ==="
grep -E '^(CBAP_MIGRATION_ENABLE|CBAP_CORE_INITIAL_RELEASE|CBAP_INITIAL_RELEASE_RATIO)' ckpt4_cbap_s3.txt
grep -cE '^(CBAP_MIGRATION_ENABLE|CBAP_CORE_INITIAL_RELEASE|CBAP_INITIAL_RELEASE_RATIO)' ckpt4_dcqcn_s3.txt
echo SEP_DONE
