cd /work/simulation/src/point-to-point/model
echo "=== the gated credit call site (1211 area) for reference ==="
sed -n '1195,1225p' rdma-hw.cc
echo
echo "=== active flow census + pfc state available at that point? ==="
grep -nE "activeControlledFlows|localPaused|downstreamPaused" rdma-hw.cc | sed -n '1,12p'
