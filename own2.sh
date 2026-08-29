cd /work/simulation/src/point-to-point/model
echo "=== (4) the AUTHORITATIVE completion event: rdma-hw.cc:4785-4800 ==="
sed -n '4783,4800p' rdma-hw.cc
echo
echo "=== is it idempotent / how often can it fire? enclosing function ==="
awk 'NR>=4740 && NR<=4795 && /^[a-zA-Z].*RdmaHw::/' rdma-hw.cc | tail -2
grep -n "^void RdmaHw::\|^bool RdmaHw::\|^uint64_t RdmaHw::" rdma-hw.cc | awk -F: '$1<4791' | tail -2
echo
echo "=== flow.active = true at 6664: the admission site ==="
sed -n '6658,6670p' rdma-hw.cc
echo
echo "=== does anything else clear active besides 4791? ==="
grep -cn "active = false" rdma-hw.cc
echo
echo "=== IsFinished(): is it a level or an edge? ==="
grep -n -A4 "bool RdmaQueuePair::IsFinished" rdma-queue-pair.cc
