# -*- coding: utf-8 -*-
# DEFECT A -- wire accounting.  Independent of defect B.
#
# The controller converted the PAYLOAD domain to the LINK domain using
# qcOnWirePacketBytes (= CBAP_MAX_WIRE_PACKET_BYTES = 1064).  That constant is a
# hand-set SAFETY MARGIN (third.cc:130, validated only as >= PACKET_PAYLOAD_SIZE)
# and every other use in rdma-hw.cc is a byte-quantity bound where OVER-
# estimating is safe.  Used as a conversion ratio numerator, over-estimating is a
# systematic accounting error: it inflated the floor by 1 share
# (65 x 100 Mbps x 0.016 = 0.104 Gbps) and produced floor_wire = 6.916 G where
# the correct value is 6.812 G.
#
# The link actually serializes packet->GetSize() (qbb-net-device.cc
# CalculateTxTime(p->GetSize())), the queue counts the same bytes
# (broadcom-egress-queue.cc m_bytesInQueueTotal += p->GetSize()) and so does the
# served-rate counter (switch-node.cc m_txBytes[ifIndex] += p->GetSize()).  For
# CC_MODE 30 that size is 1000 + 14(eth) + 20(ipv4) + 14(udp: 8 + uint16 pg +
# uint32 seq) + 0(IntHeader::NONE) = 1048 B.  Proven by
# experiment/scheme1_sba/wire_accounting_audit.py (15/15).
#
# Fix: ONE authoritative pair of conversion functions derived from the link
# header sizes, and the 1064 ratio removed from the control path.  1064 keeps its
# legitimate role as a packetization margin (the deadband quantum), which is
# where an upper bound is correct.
import io
import sys

H = '/workspaces/yunxiao/simulation/src/point-to-point/model/rdma-hw.h'
C = '/workspaces/yunxiao/simulation/src/point-to-point/model/rdma-hw.cc'
T = '/workspaces/yunxiao/simulation/scratch/third.cc'


def rd(p):
    return io.open(p, encoding='utf-8', errors='surrogateescape').read()


def wr(p, s):
    io.open(p, 'w', encoding='utf-8', errors='surrogateescape').write(s)


def need(hay, needle, n=1, tag=''):
    got = hay.count(needle)
    if got != n:
        print('ANCHOR FAIL [%s]: expected %d, found %d for:\n%s'
              % (tag, n, got, needle[:200]))
        sys.exit(2)


h, c, t = rd(H), rd(C), rd(T)

# ---------------------------------------------------------------- header ----
# Declare the authoritative conversion functions plus the derived link byte
# count.  Static so there is exactly ONE definition of the domain boundary.
if 'CbapLinkBytesPerPacket' not in h:
    a = '\t\tuint64_t qcPayloadPacketBytes;'
    need(h, a, 1, 'h:qcPayloadPacketBytes')
    h = h.replace(a, a + '''

		// --- authoritative wire accounting (defect A) -------------------
		// The controller lives entirely in the LINK byte domain, because
		// serialization, queue occupancy and served rate all count
		// packet->GetSize().  MIN_RATE is the only payload-domain input.
		// qcLinkBytesPerPacket is DERIVED from the header sizes, never from
		// CBAP_MAX_WIRE_PACKET_BYTES (a safety margin, not a ratio).
		uint64_t qcLinkBytesPerPacket;''')

    b = '\t\t\t  qcPayloadPacketBytes(0),'
    need(h, b, 1, 'h:init')
    h = h.replace(b, '\t\t\t  qcPayloadPacketBytes(0), qcLinkBytesPerPacket(0),')

# public static conversion helpers -- the ONLY sanctioned domain crossing
if 'PayloadRateToLinkRate' not in h:
    a = '\tstatic bool UsesHpccTelemetryMode(uint32_t mode);'
    need(h, a, 1, 'h:helper-anchor')
    h = h.replace(a, a + '''

	// --- the ONLY sanctioned payload<->link rate conversion (defect A) -----
	// Derived from the real per-packet link size (1048 B for CC_MODE 30), NOT
	// from CBAP_MAX_WIRE_PACKET_BYTES.  Every floor, sumR, boost, drain,
	// arrival rate, served rate and Q_stop uses the LINK domain; conversion to
	// the payload domain happens only when handing a rate to a sender.
	static uint64_t CbapLinkBytesPerPacket(void);
	static uint64_t CbapPayloadBytesPerPacket(void);
	static long double CbapPayloadToLinkRatio(void);
	static uint64_t PayloadRateToLinkRate(uint64_t payloadBps);
	static uint64_t LinkRateToPayloadRate(uint64_t linkBps);''')

# ------------------------------------------------------------------- cc ----
# Definitions.  The link size is derived from CustomHeader, which is what the
# transmit path actually serializes, so the two can never drift apart.
if 'RdmaHw::CbapLinkBytesPerPacket' not in c:
    a = 'bool RdmaHw::UsesHpccTelemetryMode(uint32_t mode)\n{'
    need(c, a, 1, 'c:helper-anchor')
    c = c.replace(a, '''uint64_t RdmaHw::CbapPayloadBytesPerPacket(void)
{
	return s_cbapConfig.qcPayloadPacketBytes > 0 ?
		s_cbapConfig.qcPayloadPacketBytes : 1000;
}

uint64_t RdmaHw::CbapLinkBytesPerPacket(void)
{
	// What the link serializes and what the queue counts: a full-payload DATA
	// packet's packet->GetSize().  CustomHeader::GetStaticWholeHeaderSize() is
	// eth(14) + ipv4(20) + udp(8 + pg + seq + IntHeader::GetStaticSize()), and
	// IntHeader::mode is NONE for CC_MODE 30, giving 1048 B.  Deriving it here
	// means it tracks the header layout automatically instead of being a second
	// hand-maintained constant.
	if (s_cbapConfig.qcLinkBytesPerPacket > 0)
		return s_cbapConfig.qcLinkBytesPerPacket;
	return CbapPayloadBytesPerPacket() +
		CustomHeader::GetStaticWholeHeaderSize();
}

long double RdmaHw::CbapPayloadToLinkRatio(void)
{
	const uint64_t pay = CbapPayloadBytesPerPacket();
	if (pay == 0)
		return 1.0L;
	return (long double)CbapLinkBytesPerPacket() / (long double)pay;
}

uint64_t RdmaHw::PayloadRateToLinkRate(uint64_t payloadBps)
{
	return (uint64_t)((long double)payloadBps * CbapPayloadToLinkRatio());
}

uint64_t RdmaHw::LinkRateToPayloadRate(uint64_t linkBps)
{
	const long double r = CbapPayloadToLinkRatio();
	return r > 0.0L ? (uint64_t)((long double)linkBps / r) : linkBps;
}

bool RdmaHw::UsesHpccTelemetryMode(uint32_t mode)
{''')

# --- call site: stop deriving the ratio from qcOnWirePacketBytes ------------
old = '''		const uint64_t payloadBytes =
			s_cbapConfig.qcPayloadPacketBytes > 0 ?
			s_cbapConfig.qcPayloadPacketBytes : 1000;
		const uint64_t wireBytes = s_cbapConfig.qcOnWirePacketBytes > 0 ?
			s_cbapConfig.qcOnWirePacketBytes : payloadBytes;'''
need(c, old, 1, 'c:callsite-ratio')
c = c.replace(old, '''		// DEFECT A: this used qcOnWirePacketBytes (= 1064, a hand-set
		// SAFETY MARGIN) as the conversion numerator, inflating the floor by
		// one 104.8 Mbps share (6.916 G observed vs 6.812 G correct).  The
		// link serializes 1048 B, so that is the only legal numerator.
		const uint64_t payloadBytes = CbapPayloadBytesPerPacket();
		const uint64_t wireBytes = CbapLinkBytesPerPacket();''')

# the two local ratio recomputations become the authoritative helper
old = '''			// Sender-effective, converted PAYLOAD -> WIRE once, here.
			const long double ratio = (long double)wireBytes /
				(long double)payloadBytes;
			const uint64_t senderWire = (uint64_t)((long double)
				flow->second.qp->m_rate.GetBitRate() * ratio);'''
need(c, old, 1, 'c:senderWire')
c = c.replace(old, '''			// Sender-effective, converted PAYLOAD -> LINK once, here,
			// through the single authoritative function.
			const uint64_t senderWire = PayloadRateToLinkRate(
				flow->second.qp->m_rate.GetBitRate());''')

old = '''		// Convert the WIRE target back to the PAYLOAD domain exactly once,
		// at the boundary where it is handed to the senders.
		const long double ratio = (long double)wireBytes /
			(long double)payloadBytes;
		long double targetPayload = ratio > 0.0L ? target / ratio : target;'''
need(c, old, 1, 'c:targetPayload')
c = c.replace(old, '''		// Convert the LINK target back to the PAYLOAD domain exactly once,
		// at the boundary where it is handed to the senders.
		long double targetPayload = target > 0.0L ?
			(long double)LinkRateToPayloadRate((uint64_t)target) : 0.0L;''')

# ---------------------------------------------------------------- third ----
# Deliberately NOT pushed from third.cc.  qcLinkBytesPerPacket stays 0 in the
# config so CbapLinkBytesPerPacket() always derives it from CustomHeader at the
# point of use -- one definition, no second hand-maintained constant to drift.
# CBAP_MAX_WIRE_PACKET_BYTES is likewise left untouched: it keeps its correct
# role as the packetization margin / deadband quantum.

wr(H, h)
wr(C, c)

print('DEFECT A applied')
print('  helpers declared      : %d' % h.count('PayloadRateToLinkRate'))
print('  helpers defined       : %d' % c.count('RdmaHw::PayloadRateToLinkRate'))
print('  qcOnWirePacketBytes in cc: %d (expect 1 = deadband margin only)'
      % c.count('qcOnWirePacketBytes'))
print('  local ratio recomputes: %d (expect 0)'
      % c.count('(long double)wireBytes /'))
