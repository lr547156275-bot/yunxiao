cd /work/simulation
grep -rn "HostQpSend" --include=*.h --include=*.cc . | head
echo "=== signature ==="
grep -rn -A4 "static void HostQpSend" --include=*.h . | head -12
echo "=== BottleneckEnqueue signature ==="
grep -rn -A4 "static void BottleneckEnqueue" --include=*.h . | head -12
