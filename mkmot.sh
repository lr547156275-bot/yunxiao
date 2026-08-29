set -u
cd /work/simulation/experiment/scheme1_sba
mkdir -p motivation
cd motivation
cp ../topology.txt .
echo "=== M1 flow table: 16-way incast H0-H15 -> H64, 256KiB, t=2.0, NO background ==="
{ echo 16
  for i in $(seq 0 15); do echo "$i 64 3 100 262144 2.0"; done
} > m1_flow.txt
head -2 m1_flow.txt | sed 's/^/  /'; echo "  ... $(($(wc -l < m1_flow.txt)-1)) flows"

echo "=== M2 flow table: 64-way H0-H63 -> H64, 1MiB, t=2.0 + background H65->H66 8Gbps ==="
{ echo 65
  echo "65 66 0 100 4000000000 0.5"
  for i in $(seq 0 63); do echo "$i 64 3 100 1048576 2.0"; done
} > m2_flow.txt
head -3 m2_flow.txt | sed 's/^/  /'; echo "  ... $(($(wc -l < m2_flow.txt)-1)) flows"

echo "=== M3 flow table: same shape as M2 (background cap 9.5G set in config) ==="
cp m2_flow.txt m3_flow.txt
echo "  m3_flow.txt = m2_flow.txt (load difference is APP_RATE_CAP_BPS)"

echo
echo "=== which leaf do M2/M3 background endpoints attach to? ==="
awk 'NR>2 && ($1==65 || $1==66) && $2>=68 {printf "  host %s -> leaf %s\n", $1, $2}' topology.txt
echo "  (H65 and H66 both on leaf 84 -> background shares the 84:1 bottleneck with the incast receiver H64)"
