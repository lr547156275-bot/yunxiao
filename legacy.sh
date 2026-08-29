cd /work/simulation/src/point-to-point/model
echo "=== the 7 legacy boost/drain/Zone matches -- what exactly are they? ==="
grep -nE "queueBoostBps|drainBps|CbapZone|ZONE_GREEN" rdma-hw.cc
echo
echo "=== the old credit fields I must NOT reuse ==="
grep -nE "delayCreditEnable|creditMaxDrainRatio|maxOversubRatio|queueDelayTargetS|queueDelayHardLimitS|creditHorizonS|queueSafetyMarginBytes" rdma-hw.h
echo
echo "=== CbapLinkRuntime: what queue/phase state already exists ==="
sed -n '/struct CbapLinkRuntime/,/};/p' rdma-hw.h | grep -nE "queuePhase|qSyncFloor|qHard|structuralStartup|normalPhase|syncBurst" | head
echo
echo "=== where the per-epoch tick computes things (entry point) ==="
grep -nE "^void RdmaHw::CbapEpochTick|ComputeDelayCreditBudget|EffectivePacingRateBps" rdma-hw.cc | head
