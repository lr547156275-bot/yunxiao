cd /work/simulation
echo "=== the existing parse idiom, 1625-1695 ==="
sed -n '1625,1650p' scratch/third.cc
echo "  ..."
sed -n '1680,1692p' scratch/third.cc
echo
echo "=== which trace source is that attached to? ==="
sed -n '1680,1684p' scratch/third.cc >/dev/null
grep -n -B2 "EgressDequeue" scratch/third.cc | head -8
