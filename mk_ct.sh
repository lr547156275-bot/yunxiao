#!/bin/bash
# telemetry OFF (bypass check) and ON (causal data), CBAP + DCQCN
set -u
cd /work/simulation/experiment/scheme1_sba || exit 2
W0=2000000000; W1=2058372997
for arm in cbap dcqcn; do
  for m in off on; do
    OUT=ct_${arm}_${m}_out
    CFG=ct_${arm}_${m}.txt
    rm -rf "$OUT"; mkdir -p "$OUT"
    sed "s#sr_${arm}_s3_out#${OUT}#g" sr_${arm}_s3.txt > "$CFG"
    if [ "$m" = "on" ]; then
      for kv in "CAUSAL_QUEUE_TRACE_FILE ${OUT}/causal_queue.csv" \
                "CAUSAL_PACER_TRACE_FILE ${OUT}/causal_pacer.csv" \
                "CAUSAL_TRACE_START_NS $W0" "CAUSAL_TRACE_END_NS $W1"; do
        k=${kv%% *}
        grep -q "^${k}[[:space:]]" "$CFG" && sed -i "s#^${k}[[:space:]].*#${kv}#" "$CFG" || echo "$kv" >> "$CFG"
      done
    fi
    LD_LIBRARY_PATH=/work/simulation/build /work/simulation/build/scratch/third "$CFG" > "$OUT/run.log" 2>&1
    echo "${arm}_${m} exit=$?" >> /tmp/ct.log
  done
done
echo CT_ALL_DONE >> /tmp/ct.log
