set -u
L=/work/matrix_logs
echo "=== s4 done ==="
ls $L/m_*_s4_seed2.done 2>/dev/null | xargs -n1 basename 2>/dev/null | sed 's/^/  /'
echo "=== running ==="
ps -o pcpu,etime,args -p $(pgrep -d, -x third 2>/dev/null) 2>/dev/null | tail -n +2 | sed 's/^/  /' || echo "  none"
echo "=== driver alive? ==="
pgrep -f matrix_par >/dev/null 2>&1 && echo "  yes" || echo "  NO"
echo "=== any FAIL? ==="
grep -E "^(FAIL|OK).*s4" $L/matrix_par_driver.log 2>/dev/null | sed 's/^/  /' || echo "  no s4 lines yet"
