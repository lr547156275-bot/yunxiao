cd /work/simulation
echo "=== RdmaQpDequeue signature + an existing consumer ==="
sed -n '213,215p' src/point-to-point/model/qbb-net-device.cc
grep -n -A6 'TraceConnectWithoutContext("RdmaQpDequeue"' scratch/third.cc | head -14
echo
echo "=== QbbEnqueue signature + an existing consumer ==="
sed -n '207,209p' src/point-to-point/model/qbb-net-device.cc
grep -n -A5 'bottleneck->TraceConnectWithoutContext("QbbEnqueue"' scratch/third.cc | head -12
