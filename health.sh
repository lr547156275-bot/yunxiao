set -u
L=/work/matrix_logs
echo "=== progress by scenario ==="
for t in s1 s2 s3 s6 s4 s5; do
  n=$(ls $L/m_*_${t}_seed2.done 2>/dev/null | wc -l)
  printf "  %-3s %d/5\n" "$t" "$n"
done
echo "=== running now ==="
pgrep -a -x third 2>/dev/null | grep -oE "m_[a-z]+_s[0-9]_seed2" | sed 's/^/  /' || echo "  none"
echo "=== resources ==="
df -h /work | awk 'NR==2{printf "  disk: %s free (%s used)\n", $4, $5}'
free -m | awk 'NR==2{printf "  mem : %d MB available\n", $7}'
uptime | sed 's/^/  load: /'
echo "=== any failure so far? ==="
grep -cE "^FAIL" $L/matrix_par_driver.log 2>/dev/null | sed 's/^/  FAIL lines: /'
echo "=== all manifests carry both hashes? ==="
tot=$(ls $L/m_*_s[1-6]_seed2.manifest 2>/dev/null | wc -l)
b=$(grep -l "^binary_sha256=0156d0ba" $L/m_*_s[1-6]_seed2.manifest 2>/dev/null | wc -l)
p=$(grep -l "^p2p_lib_sha256=0bacef18" $L/m_*_s[1-6]_seed2.manifest 2>/dev/null | wc -l)
echo "  manifests=$tot  correct third=$b  correct p2p_lib=$p"
