cd /work/simulation
echo "=== TracedCallback declarations for the two sources ==="
grep -nE "m_traceQpDequeue|m_traceEnqueue" src/point-to-point/model/qbb-net-device.h
echo
echo "=== ShortGapPipeline header, searched only under src/ ==="
grep -rln "class ShortGapPipeline" src/ 2>/dev/null
