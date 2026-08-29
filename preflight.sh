set -u
cd /work/simulation
D=experiment/scheme1_sba
L=/work/matrix_logs
echo "=== 1. hash gate will pass? ==="
T=$(sha256sum build/scratch/third | cut -d' ' -f1)
P=$(sha256sum build/libns3.18-point-to-point-debug.so | cut -d' ' -f1)
WT=$(awk -F= '$1=="binary_sha256"{print $2}' $L/matrix_baseline.manifest)
WP=$(awk -F= '$1=="p2p_lib_sha256"{print $2}' $L/matrix_baseline.manifest)
[ "$T" = "$WT" ] && echo "  third   OK" || echo "  third   MISMATCH"
[ "$P" = "$WP" ] && echo "  p2p lib OK" || echo "  p2p lib MISMATCH"
echo "=== 2. runner gates on both, refuses parallel ==="
grep -c "p2p_lib_sha256" $D/run_matrix.sh | sed 's/^/  p2p_lib refs: /'
grep -n "MAX_JOBS must be 1" $D/run_matrix.sh | head -1 | sed 's/^/  /'
echo "=== 3. no stale done flags ==="
ls $L/m_*_s[1-6]_seed2.done 2>/dev/null | wc -l | sed 's/^/  matrix done flags: /'
echo "=== 4. QLEN_MON_END >= stop for all six ==="
for t in s1 s2 s3 s4 s5 s6; do
  s=$(awk '/^SIMULATOR_STOP_TIME/{print $2}' $D/${t}_config.txt)
  q=$(awk '/^QLEN_MON_END/{print $2}' $D/${t}_config.txt)
  awk -v t=$t -v s=$s -v q=$q 'BEGIN{printf "  %s stop=%.1fs qlen_end=%.1fs %s\n", t, s, q/1e9, (q >= s*1e9 ? "OK" : "VIOLATION")}'
done
echo "=== 5. disk ==="
df -h /work | tail -1 | awk '{print "  " $4 " free (" $5 " used)"}'
echo "=== 6. git commit recorded by manifests ==="
git -C /work rev-parse --short HEAD | sed 's/^/  HEAD: /'
