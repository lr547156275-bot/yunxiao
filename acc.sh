cd /work/simulation/src/point-to-point/model
echo "=== does SwitchNode expose the mmu / per-ingress counters? ==="
grep -nE "m_mmu|GetEgressQueueBytes|GetRxBytes|public:" switch-node.h | head -20
echo
echo "=== switch-mmu.h: which members are public vs private? ==="
sed -n '20,70p' switch-mmu.h
