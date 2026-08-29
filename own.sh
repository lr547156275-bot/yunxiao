cd /work/simulation/src/point-to-point/model
echo "=== (1) every qcProtectedQps insert/erase/clear ==="
grep -n "qcProtectedQps" rdma-hw.cc
echo
echo "=== (2) every ownsRate assignment ==="
grep -n "ownsRate" rdma-hw.cc
echo
echo "=== qcLedger erase / clear sites ==="
grep -n "qcLedger" rdma-hw.cc
echo
echo "=== (3) where is CbapFlowRuntime.active / finished SET? ==="
grep -nE "\.active = |\.finished = |second\.active =|second\.finished =" rdma-hw.cc | head -20
