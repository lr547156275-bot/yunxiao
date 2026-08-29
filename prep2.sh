set -u
cd /work/simulation
echo "=== new binary hashes ==="
sha256sum build/scratch/third build/libns3.18-point-to-point-debug.so | cut -c1-24 | sed 's/^/  /'
echo "=== unit checks (the python model mirrors the C++ law) ==="
python3 experiment/scheme1_sba/queue_credit_unit_check.py 2>&1 | tail -13
