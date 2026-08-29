set -u
cd /work/simulation
echo "=== build result ==="
grep -E "finished successfully|Build failed" /tmp/b.txt | head -2 | sed 's/^/  /'
echo "=== binaries ==="
for f in build/scratch/third build/libns3.18-point-to-point-debug.so; do
  printf "  %-46s %s  mtime=%s\n" "$(basename $f)" "$(sha256sum $f | cut -c1-20)" "$(stat -c %y "$f" | cut -c12-19)"
done
echo "  now = $(date +%H:%M:%S)"
echo "=== new symbol present? ==="
nm -CD build/libns3.18-point-to-point-debug.so | grep -c "ComputeDelayCreditBudget\|s_cbapDelayCreditRecords" | sed 's/^/  symbols: /'
