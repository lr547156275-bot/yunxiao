cd /work/simulation/src/point-to-point/model
echo "=== every symbol mentioning migration ==="
grep -nE "[Mm]igration|migrat" rdma-hw.cc | head -60
