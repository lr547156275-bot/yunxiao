set -u
echo "=== per-process CPU efficiency: want both near 100 pct ==="
ps -o pid,pcpu,rss,etime,time,args -p $(pgrep -d, -x third) 2>/dev/null | sed 's/^/  /'
echo "=== host cpu breakdown ==="
top -bn2 -d 2 | grep "^%Cpu" | tail -1 | sed 's/^/  /'
free -m | awk 'NR==2{printf "  mem: %d MB avail of %d MB\n", $7, $2}'
