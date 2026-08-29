set -u
cd /work/simulation
echo "=== does pg map directly to qIndex? ==="
grep -n "GetPriority()\|qIndex = \|ch.udp.pg\|m_priority" src/point-to-point/model/switch-node.cc | head -6 | sed 's/^/  /'
echo
echo "=== CRITICAL: what pg did the FROZEN matrix give its background flow? ==="
cd experiment/scheme1_sba
for t in s1 s2 s3 s4 s5 s6; do
  awk -v tag=$t 'NR==2{printf "  %s background: src=%s dst=%s pg=%s\n", tag, $1, $2, $3}' ${t}_flow.txt
done
echo "=== and the incast pg? ==="
awk 'NR==3{printf "  s3 incast: pg=%s\n", $3}' s3_flow.txt
echo
echo "=== so in the FROZEN matrix too, background=pg0 (ECN-exempt), incast=pg3 ==="
echo "=== does queue 0 also skip PFC / share the same egress accounting? ==="
grep -n "qIndex == 0\|qIndex==0" ../../src/point-to-point/model/switch-mmu.cc ../../src/point-to-point/model/switch-node.cc 2>/dev/null | sed 's/^/  /'
