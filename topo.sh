cd /work/simulation/experiment/scheme1_sba
f=topology.txt
echo "=== header: n_node n_switch n_link ==="; head -1 $f
echo "=== switch list (line 2) ==="; sed -n '2p' $f
echo "=== all links at 84 ==="; awk 'NR>2 && ($1==84||$2==84)' $f
echo "=== all links at 83 ==="; awk 'NR>2 && ($1==83||$2==83)' $f | head -3
echo "  (83 link count: $(awk 'NR>2 && ($1==83||$2==83)' $f | wc -l))"
echo
echo "=== how many devices does node 84 end up with? grep GetNDevices usage ==="
grep -nE "ConfigNPort|GetNDevices" /work/simulation/scratch/third.cc | head -4
echo
echo "=== the shift variable: where set ==="
grep -nB3 "pfc_a_shift\[j\] = shift" /work/simulation/scratch/third.cc | head -12
