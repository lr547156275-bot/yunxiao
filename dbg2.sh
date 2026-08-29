cd /work/simulation
echo "=== full context 4395-4445 ==="
sed -n '4395,4445p' scratch/third.cc | cat -n | awk '{printf "%d: %s\n", $1+4394, substr($0, index($0,$2))}'
