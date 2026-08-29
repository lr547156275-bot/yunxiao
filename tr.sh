cd /work/simulation
echo "=== existing packet-level trace sources on the device/queue ==="
grep -nE "TraceConnectWithoutContext|TraceConnect" scratch/third.cc | head -12
echo
echo "=== qbb-net-device trace sources ==="
grep -nE "AddTraceSource" src/point-to-point/model/qbb-net-device.cc | head -10
echo
echo "=== switch-node trace sources ==="
grep -nE "AddTraceSource|m_traceEnqueue|m_traceDequeue" src/point-to-point/model/switch-node.cc src/point-to-point/model/switch-node.h | head
echo
echo "=== BEgressQueue trace sources ==="
grep -nE "AddTraceSource" src/point-to-point/model/broadcom-egress-queue.cc | head
