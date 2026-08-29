cd /work/simulation
echo "=== the TracedCallback member declarations (authoritative signature) ==="
grep -nE "m_traceQpDequeue|m_traceEnqueue" src/point-to-point/model/qbb-net-device.h
echo
echo "=== find ShortGapPipeline header ==="
grep -rln "class ShortGapPipeline" . 2>/dev/null
grep -rn "static void HostQpSend\|static void BottleneckEnqueue" $(grep -rln "class ShortGapPipeline" . 2>/dev/null) 2>/dev/null | head
