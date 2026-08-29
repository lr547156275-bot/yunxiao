cd /work/simulation
echo "=== where is packetPayloadBytes declared? ==="
grep -rn "packetPayloadBytes" src/point-to-point/model/*.h | head -5
echo
echo "=== and how is it set from third.cc? ==="
grep -n "packetPayloadBytes" scratch/third.cc | head -5
echo
echo "=== CbapConfig fields near qcOnWirePacketBytes ==="
grep -n -B2 -A2 "qcOnWirePacketBytes" src/point-to-point/model/rdma-hw.h | head -14
