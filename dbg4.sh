cd /work/simulation
echo "=== rdma-hw.cc:4795-4815 : where crfm.flowId is set ==="
sed -n '4795,4815p' src/point-to-point/model/rdma-hw.cc
echo
echo "=== is that on the SENDER (AddQueuePair) or receiver path? ==="
grep -n -B25 "qp->crfm.flowId = pending->second.flowId;" src/point-to-point/model/rdma-hw.cc | grep -nE "^[0-9]+-(void|RdmaHw::|.*::)" | head -4
