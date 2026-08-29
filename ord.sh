cd /work/simulation/src/point-to-point/model
echo "=== where is CbapLinkRuntime declared vs my function (line numbers) ==="
grep -n "struct CbapLinkRuntime" rdma-hw.h
grep -n "QueueControllerEpoch" rdma-hw.h
grep -n "ComputeDelayCreditBudget" rdma-hw.h
echo
echo "=== how does ComputeDelayCreditBudget declare its CbapLinkRuntime param? ==="
grep -n -A4 "ComputeDelayCreditBudget" rdma-hw.h
