cd /work/simulation
echo "=== is crfm.flowId the same id space the controller uses? ==="
grep -nE "crfm\.flowId" src/point-to-point/model/rdma-hw.cc | head -6
echo
echo "=== flow=0 is the background flow; does it live on a HOST node? ==="
echo "  s3_flow.txt line 2: $(sed -n '2p' experiment/scheme1_sba/s3_flow.txt)  -> src=65 dst=64"
echo "  host 65 nodeType:"
grep -nE "GetNodeType" scratch/third.cc | head -3
echo
echo "=== did the QpDequeue observer get connected at all? count devices visited ==="
grep -n -B3 -A6 "CbapActuationOnQpDequeue, hdev" scratch/third.cc
echo
echo "=== is the install block AFTER n is populated? line numbers ==="
grep -n "s_cbapActuationHook = \&CbapActuationOnRateCommand" scratch/third.cc
grep -n "MakeCallback(&ReadCbapPort)" scratch/third.cc
grep -nE "^\s*n\.Create|n = NodeContainer|CreateObject<Node>" scratch/third.cc | head -4
