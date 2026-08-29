set -u
cd /work/simulation
CC=gcc-7 CXX=g++-7 python2 waf build > /tmp/build_out.txt 2>&1
code=$?
echo "exit=$code"
grep -E "finished successfully|Build failed" /tmp/build_out.txt | head -2
echo "=== errors (if any) ==="
grep -E "error:|Error " /tmp/build_out.txt | head -12 || echo "  none"
echo "=== hashes after build ==="
printf "  third  : %s\n" "$(sha256sum build/scratch/third | cut -d' ' -f1)"
printf "  p2p lib: %s\n" "$(sha256sum build/libns3.18-point-to-point-debug.so | cut -d' ' -f1)"
echo "=== new symbols present? ==="
nm -CD build/libns3.18-point-to-point-debug.so | grep -c "EtaFeasibilityRecords\|s_cbapLastEtaEffective"
