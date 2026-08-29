set -u
L=/work/matrix_logs
echo "=== measured wall_seconds from the PRE-FREEZE run (same machine, same work) ==="
for t in s1 s2 s3 s6 s4 s5; do
  tot=0; n=0; line=""
  for a in dcqcn dctcp timely hpcc cbapsba; do
    f=$L/pre_freeze_run/m_${a}_${t}_seed2.manifest
    [ -f "$f" ] || continue
    w=$(awk -F= '$1=="wall_seconds"{print $2}' "$f")
    [ -n "$w" ] || continue
    tot=$((tot+w)); n=$((n+1))
    line="$line $a=$((w/60))m"
  done
  [ "$n" -gt 0 ] && printf "  %-3s n=%d  total=%4d min  avg=%3d min |%s\n" "$t" "$n" "$((tot/60))" "$((tot/n/60))" "$line"
  GT=$((${GT:-0}+tot))
done
echo
printf "  ===> all measured cells: %d min = %.1f h\n" "$((GT/60))" "$(echo $GT | awk '{print $1/3600}')"
