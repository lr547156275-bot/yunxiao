cd /work/simulation/src/point-to-point/model
echo "=== protected-set loop ==="
awk '/protected QP set: every controlled flow/,/rEffective \+= runtime.config.backgroundBps/' rdma-hw.cc
echo
echo "=== is the background flow in s_cbapFlows at all? ==="
grep -n "backgroundBps" rdma-hw.cc | head -6
