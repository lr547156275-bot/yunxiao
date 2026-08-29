cd /work/simulation
grep -nE "HostQpSend|BottleneckEnqueue" scratch/third.cc | head
echo "=== definition ==="
grep -n -B2 -A10 "void ShortGapPipeline::HostQpSend" scratch/third.cc | head -18
echo "=== and BottleneckEnqueue ==="
grep -n -B2 -A10 "void ShortGapPipeline::BottleneckEnqueue" scratch/third.cc | head -18
