cd /work/simulation/src/point-to-point/model
echo "=== how do other STATIC cbap functions get MIN_RATE? ==="
grep -nE "m_minRate" rdma-hw.cc | head -8
echo
echo "=== is there a static/global min rate for the cbap path? ==="
grep -nE "static.*minRate|s_cbap.*[Mm]inRate|minRateBps" rdma-hw.cc | head -8
echo
echo "=== the eta_feasibility code used minRateBps -- where from? ==="
grep -n -B4 "minRateBps" rdma-hw.cc | head -20
