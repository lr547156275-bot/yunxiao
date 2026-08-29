cd /work/simulation/src/point-to-point/model
echo "=== every write to m_rate on a CBAP path ==="
grep -nE "m_rate *= *|m_rate\.Set|SetRate|m_rate = DataRate" rdma-hw.cc | head -30
echo
echo "=== the floor: legacy_floor_rate_bps / protection floor / minRate clamps ==="
grep -nE "legacyFloor|protectionFloor|m_minRate|minRate" rdma-hw.cc | grep -iE "max\(|clamp|floor" | head -20
