set -u
cd /work/simulation
echo "=== Q1: is the cap applied only as a ceiling, so DCQCN can still cut the rate? ==="
sed -n '6763,6766p' src/point-to-point/model/rdma-hw.cc | sed 's/^/  /'
echo "  (this is in the rate-update path: DCQCN computes new_rate, cap only clamps the top)"
echo
echo "=== Q1: does the background flow take the same AddQueuePair path (no special case)? ==="
grep -n "AddQueuePair" scratch/third.cc | head -3 | sed 's/^/  /'
grep -nE "pg\s*==\s*0|priority.*==.*0|if.*pg" src/point-to-point/model/rdma-hw.cc | grep -iE "skip|exempt|bypass|no.*ecn|return" | head -5 | sed 's/^/  /' || echo "  no pg-based exemption found in rdma-hw.cc"
echo
echo "=== Q1: ECN marking site -- is it keyed on pg/priority at all? ==="
grep -n "CheckIngressAdmission\|ShouldSendCN\|EcnMark\|CheckShouldMark" src/point-to-point/model/switch-mmu.cc src/point-to-point/model/switch-node.cc 2>/dev/null | head -6 | sed 's/^/  /'
