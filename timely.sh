set -u
cd /work/simulation/src/point-to-point/model
echo "=== what TIMELY actually measures ==="
sed -n '7269,7290p' rdma-hw.cc | grep -nE "rtt|Rtt|ts|delay|gradient|m_timely" | head -10 | sed 's/^/  /'
echo
echo "=== KEY: does pg change which QUEUE a packet waits in? ==="
grep -n "qIndex" /work/simulation/src/point-to-point/model/switch-node.cc | sed -n '1,6p' | sed 's/^/  /'
