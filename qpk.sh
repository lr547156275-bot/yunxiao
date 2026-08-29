cd /work/simulation
echo "=== stable QP key fields available on RdmaQueuePair ==="
grep -nE "uint32_t (sip|dip)|uint16_t (sport|dport)|uint16_t m_pg|uint8_t m_pg" src/point-to-point/model/rdma-queue-pair.h | head
echo
echo "=== packet sequence: what identifies a DATA packet at the bottleneck? ==="
grep -nE "class QbbHeader|GetSeq|SeqTsHeader" src/point-to-point/model/qbb-header.h 2>/dev/null | head -5
echo "  --- what headers does a data packet carry (from the enqueue path)? ---"
sed -n '405,420p' src/point-to-point/model/qbb-net-device.cc
echo
echo "=== snd_nxt available on qp at dequeue time? ==="
grep -nE "snd_nxt|m_snd_nxt" src/point-to-point/model/rdma-queue-pair.h | head -4
