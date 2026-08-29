cd /work/simulation
echo "=== what timestamps already exist in the epoch path? ==="
grep -nE "sampleTimeNs|deliveryTimeNs|decisionTimeNs" src/point-to-point/model/rdma-hw.cc | head -12
echo
echo "=== the snapshot struct fields ==="
sed -n '/struct CbapPortSnapshot/,/};/p' src/point-to-point/model/rdma-hw.h | head -25
echo
echo "=== where is the snapshot taken (third.cc side) ==="
grep -nE "sample_time_ns|delivery_time_ns|CbapPortSnapshot|PushCbapTelemetry|feedbackHorizon" scratch/third.cc | head -12
