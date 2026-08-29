cd /work/simulation
echo "=== what does the egress queue count: payload or wire bytes? ==="
grep -rn "GetNBytesTotal\|m_bytesInQueue\|AddBytes" src/point-to-point/model/broadcom-egress-queue.* 2>/dev/null | head -8
echo
echo "=== packet size at enqueue: does it include headers? ==="
grep -n "PACKET_PAYLOAD_SIZE" experiment/scheme1_sba/qc_s3_rho090.txt
grep -n "packet_payload_size" scratch/third.cc | head -4
echo
echo "=== header bytes added on the RDMA send path ==="
grep -rnE "AddHeader|GetSerializedSize" src/point-to-point/model/rdma-hw.cc | head -8
echo
echo "=== observed tx_bytes_delta granularity was 1048 B; payload configured? ==="
awk '/^PACKET_PAYLOAD_SIZE/{print "  PACKET_PAYLOAD_SIZE = "$2}' experiment/scheme1_sba/qc_s3_rho090.txt
awk '/^CBAP_MAX_WIRE_PACKET_BYTES/{print "  CBAP_MAX_WIRE_PACKET_BYTES = "$2}' experiment/scheme1_sba/qc_s3_rho090.txt
