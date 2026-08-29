# -*- coding: utf-8 -*-
# u64 widen #2: GetNxtPacket stored the 64-bit GetBytesLeft() in a uint32.
# When a flow's remaining bytes hit an exact multiple of 2^32 the truncated
# view reads 0, the packet builder produces nothing, and the QP sleeps
# forever (both 400G cells froze at released - snd_nxt == 4,294,967,296
# exactly; 10G/200G backgrounds are < 2^32 and never trip it).  Behaviour
# for values < 2^32 is bit-identical -- proven by the usual twin regression.
import io
import sys

P = '/work/simulation/src/point-to-point/model/rdma-hw.cc'
t = io.open(P, encoding='utf-8', errors='surrogateescape').read()
if 'bytes_left64' in t:
    print('already applied')
    sys.exit(0)
old = ('Ptr<Packet> RdmaHw::GetNxtPacket(Ptr<RdmaQueuePair> qp){\n'
       '\tuint32_t payload_size = qp->GetBytesLeft();\n'
       '\tif (m_mtu < payload_size)\n'
       '\t\tpayload_size = m_mtu;')
new = ('Ptr<Packet> RdmaHw::GetNxtPacket(Ptr<RdmaQueuePair> qp){\n'
       '\t// GetBytesLeft is 64-bit; a u32 copy made remaining == k*2^32\n'
       '\t// read as 0 and froze the QP (>4.29GB flows at 400G).\n'
       '\tuint64_t bytes_left64 = qp->GetBytesLeft();\n'
       '\tuint32_t payload_size = bytes_left64 > (uint64_t)m_mtu ?\n'
       '\t\tm_mtu : (uint32_t)bytes_left64;')
n = t.count(old)
print('anchor count=%d %s' % (n, 'OK' if n == 1 else 'FAIL'))
if n != 1:
    sys.exit(2)
io.open(P, 'w', encoding='utf-8',
        errors='surrogateescape').write(t.replace(old, new, 1))
print('payload64 fix applied (inert for flows < 2^32 remaining)')
