cd /work/simulation/src/point-to-point/model
echo "=== rdma-hw.cc:1878 context ==="
sed -n '1845,1885p' rdma-hw.cc
echo
echo "=== is that site reached in core mode? which batchId/available ==="
grep -n "AdmitBatch\|ReadmitHeld" rdma-hw.cc
