cd /work/simulation/src/point-to-point/model
echo "=== where EvaluateCbapSbaMigration writes the rate (the command instant) ==="
sed -n '2360,2400p' rdma-hw.cc
echo
echo "=== is there an existing per-flow rate-change trace hook? ==="
grep -nE "cbapRateTransition|RecordCbapRateTransition|rate_transition" rdma-hw.cc | head -6
