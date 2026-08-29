set -u
L=/work/matrix_logs
echo "=== progress ==="
for t in s1 s2 s3 s6 s4 s5; do printf "  %-3s %d/5\n" "$t" "$(ls $L/m_*_${t}_seed2.done 2>/dev/null | wc -l)"; done
echo "=== running ==="
pgrep -a -x third 2>/dev/null | grep -oE "m_[a-z]+_s[0-9]_seed2" | sed 's/^/  /' || echo "  none"
echo "=== S4 wall times so far (serial ref: ~48-55 min each) ==="
for a in dcqcn dctcp timely hpcc cbapsba; do
  f=$L/m_${a}_s4_seed2.manifest
  [ -f "$f" ] && printf "  %-8s %s s (%s min)\n" "$a" "$(awk -F= '$1=="wall_seconds"{print $2}' $f)" "$(awk -F= '$1=="wall_seconds"{printf "%.0f", $2/60}' $f)"
done
echo "=== resources (S4/S5 are the heavy ones) ==="
df -h /work | awk 'NR==2{printf "  disk: %s free (%s used)\n", $4, $5}'
free -m | awk 'NR==2{printf "  mem : %d MB available\n", $7}'
ps -o pcpu,rss,args -p $(pgrep -d, -x third 2>/dev/null) 2>/dev/null | tail -n +2 | awk '{printf "  %5s%% %6.0f MB  %s\n", $1, $2/1024, $NF}'
echo "=== failures ==="
grep -cE "^FAIL" $L/matrix_par_driver.log 2>/dev/null | sed 's/^/  FAIL lines: /'
