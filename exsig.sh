cd /work/simulation
echo "=== exact signatures of the existing consumers ==="
grep -nE "static void (HostQpSend|BottleneckEnqueue)" scratch/third.cc | head -6
echo "---"
grep -n -A8 "static void HostQpSend" scratch/third.cc | head -14
echo "---"
grep -n -A8 "static void BottleneckEnqueue" scratch/third.cc | head -14
