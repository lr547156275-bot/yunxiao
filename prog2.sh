set -u
L=/work/matrix_logs
D=/work/simulation/experiment/scheme1_sba
echo "=== driver alive? ==="
pgrep -f matrix_par >/dev/null 2>&1 && echo "  yes" || echo "  NO - driver gone"
echo "=== concurrent cells + efficiency ==="
ps -o pcpu,rss,etime,args -p $(pgrep -d, -x third 2>/dev/null) 2>/dev/null | tail -n +2 | sed 's/^/  /' || echo "  none running"
echo "=== simulated progress of each running cell ==="
for f in $(pgrep -a -x third 2>/dev/null | grep -oE "m_[a-z]+_s[0-9]_seed2"); do
  ts=$D/${f}_out/selected_link_timeseries.csv
  [ -f "$ts" ] && awk -F, -v n="$f" 'NR>1{t=$1} END{printf "  %-24s sim_t=%.3f s  rows=%d\n", n, t, NR-1}' "$ts"
done
echo "=== done flags ==="
ls $L/m_*_s[1-6]_seed2.done 2>/dev/null | xargs -n1 basename 2>/dev/null | sed 's/^/  /'
echo "=== driver log tail ==="
tail -4 $L/matrix_par_driver.log
