cd /work/simulation/src/point-to-point/model
echo "=== every CheckConservation call site ==="
grep -rn "CheckConservation" . ../../../scratch/ 2>/dev/null
echo
echo "=== what does it compare (body) ==="
sed -n '432,454p' cbap-sba.cc
echo
echo "=== the two args at the AdmitBatch call site ==="
sed -n '278,296p' cbap-sba.cc
