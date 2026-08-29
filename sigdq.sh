cd /work/simulation
echo "=== EgressDequeue trace source signature ==="
sed -n '70,76p' src/point-to-point/model/switch-node.cc
grep -nE "m_traceEgressDequeue" src/point-to-point/model/switch-node.h src/point-to-point/model/switch-node.cc
echo
echo "=== the existing consumer's parameter list (line ~1744 connect) ==="
sed -n '1738,1750p' scratch/third.cc
echo
echo "=== and its function signature ==="
grep -n -B3 "qIndex == 0 ||" scratch/third.cc | head -12
