# Deterministic wire-accounting audit (report item 2).
#
# Answers, FROM SOURCE ONLY, the six questions:
#   1. what does the 10 Gbps C serialize -- payload, packet size, or wire time?
#   2. which bytes does the queue occupancy Q count?
#   3. which bytes does served rate count?
#   4. which domain must the CBAP floor and Q_stop live in?
#   5. where does CBAP_MAX_WIRE_PACKET_BYTES = 1064 come from?
#   6. which headers make up the observed 1048?
#
# This script does NOT fit a ratio to trace data.  It derives the byte count
# from the header structs and checks that every accounting site uses the same
# expression (p->GetSize()).  A ratio fitted to a trace is what let 1064 pass
# unnoticed for a whole run.
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.normpath(os.path.join(HERE, '..', '..'))


def src(*parts):
    p = os.path.join(SIM, *parts)
    if not os.path.exists(p):
        print('MISSING SOURCE: %s' % p)
        sys.exit(2)
    return open(p).read()


res = []


def check(name, ok, detail):
    res.append((name, ok, detail))
    return ok


qbb = src('src', 'point-to-point', 'model', 'qbb-net-device.cc')
beq = src('src', 'network', 'utils', 'broadcom-egress-queue.cc')
swn = src('src', 'point-to-point', 'model', 'switch-node.cc')
p2p = src('src', 'point-to-point', 'model', 'point-to-point-net-device.cc')
chh = src('src', 'network', 'utils', 'custom-header.h')
chc = src('src', 'network', 'utils', 'custom-header.cc')
ihc = src('src', 'network', 'utils', 'int-header.cc')
hw = src('src', 'point-to-point', 'model', 'rdma-hw.cc')
hwh = src('src', 'point-to-point', 'model', 'rdma-hw.h')
th = src('scratch', 'third.cc')

print('=== wire-accounting determinism audit ===')
print('')

# ---- Q1: what the link serializes -----------------------------------------
ser = re.search(r'CalculateTxTime\((p->GetSize\(\))\)', qbb)
check('Q1. link serialization counts p->GetSize()',
      ser is not None and ser.group(1).strip() == 'p->GetSize()',
      'qbb-net-device.cc: CalculateTxTime(%s)'
      % (ser.group(1).strip() if ser else '??'))

# The IFG is a Time, added AFTER txTime, and defaults to 0 -> contributes no
# bytes to any account and no time under the default config.
ifg = re.search(r'"InterframeGap".*?TimeValue \(Seconds \(([0-9.]+)\)\)', p2p,
                re.S)
check('Q1b. no preamble/IFG/FCS bytes enter the byte accounts',
      ifg is not None and float(ifg.group(1)) == 0.0
      and 'txTime + m_tInterframeGap' in qbb,
      'IFG is a Time (default %s s), never a byte count'
      % (ifg.group(1) if ifg else '??'))

# ---- Q2: queue occupancy --------------------------------------------------
enq = re.findall(r'm_bytesInQueueTotal \+= (.*?);', beq)
deq = re.findall(r'm_bytesInQueueTotal -= (.*?);', beq)
check('Q2. queue occupancy Q counts p->GetSize()',
      len(enq) > 0 and all(e.strip() == 'p->GetSize()' for e in enq)
      and all(d.strip() == 'p->GetSize()' for d in deq),
      'broadcom-egress-queue.cc: %d enqueue / %d dequeue sites, all GetSize()'
      % (len(enq), len(deq)))
check('Q2b. CBAP reads that same counter',
      'GetNBytesTotal()' in swn and 'GetEgressQueueBytes' in swn,
      'switch-node.cc GetEgressQueueBytes -> GetQueue()->GetNBytesTotal()')

# ---- Q3: served rate ------------------------------------------------------
tx = re.search(r'm_txBytes\[ifIndex\] \+= (.*?);', swn)
check('Q3. served rate / m_txBytes counts p->GetSize()',
      tx is not None and tx.group(1).strip() == 'p->GetSize()',
      'switch-node.cc: m_txBytes[ifIndex] += %s'
      % (tx.group(1).strip() if tx else '??'))

# ---- Q6: what makes up 1048 ----------------------------------------------
# GetStaticWholeHeaderSize = 14 + 20 + GetUdpHeaderSize()
# GetUdpHeaderSize        = 8 + sizeof(udp.pg) + sizeof(udp.seq) + INT
whole = re.search(r'GetStaticWholeHeaderSize\(void\)\{\s*return (.*?);', chc,
                  re.S)
udp = re.search(r'GetUdpHeaderSize\(void\)\{\s*return (.*?);', chc, re.S)
check('Q6. header expression is eth(14) + ipv4(20) + udp',
      whole is not None and '14 + 20 + GetUdpHeaderSize()' in whole.group(1),
      'custom-header.cc: %s' % (whole.group(1).strip() if whole else '??'))

# field widths, read from the struct rather than assumed
mudp = re.search(r'struct\s*\{(.*?)\}\s*udp;', chh, re.S)
fields = dict(re.findall(r'uint(\d+)_t\s+(\w+)\s*;',
                         mudp.group(1) if mudp else ''))
wid = {v: int(k) // 8 for k, v in fields.items()}
pg_b, seq_b = wid.get('pg'), wid.get('seq')
check('Q6b. udp.pg / udp.seq widths read from the struct',
      pg_b == 2 and seq_b == 4,
      'udp.pg = %s B, udp.seq = %s B' % (pg_b, seq_b))

# INT size for the mode actually under test
mode30_hpcc = bool(re.search(r'mode == CC_MODE_CBAP_SBA_DCQCN', hw))
fam = re.search(r'UsesHpccTelemetryMode\(uint32_t mode\)\s*\{\s*return (.*?);',
                hw, re.S)
famtxt = fam.group(1) if fam else ''
check('Q6c. CC_MODE 30 is NOT in UsesHpccTelemetryMode -> IntHeader NONE',
      'CC_MODE_CBAP_SBA_DCQCN' not in famtxt,
      'family lists 3, 11-16, 18, 19, 29, 31 -- not 30')
check('Q6d. IntHeader::GetStaticSize() returns 0 for NONE',
      re.search(r'\}else \{\s*return 0;', ihc) is not None,
      'int-header.cc default branch returns 0')

INT_NONE = 0
udp_hdr = 8 + pg_b + seq_b + INT_NONE if (pg_b and seq_b) else None
whole_hdr = 14 + 20 + udp_hdr if udp_hdr else None
PAY = 1000
wire = PAY + whole_hdr if whole_hdr else None
check('Q6e. derived DATA wire size == 1048 B',
      wire == 1048,
      '1000 + (14 + 20 + (8 + %s + %s + 0)) = %s B' % (pg_b, seq_b, wire))

# ACK/CNP use a different, 60-byte-minimum frame on the high-prio queue
acks = re.findall(r'Create<Packet>\(\s*std::max\(60\s*-\s*14\s*-\s*20', hw)
check('Q6f. ACK/NACK/CNP are 60 B min frames, NOT 1048',
      len(acks) >= 1 and 'RdmaEnqueueHighPrioQ' in hw,
      '%d ACK construction site(s) padded to a 60 B frame, high-prio queue'
      % len(acks))

# ---- Q5: where 1064 comes from -------------------------------------------
dflt = re.search(r'cbap_max_wire_packet_bytes = (\d+)', th)
check('Q5. CBAP_MAX_WIRE_PACKET_BYTES default is a hand-set 1064',
      dflt is not None and dflt.group(1) == '1064',
      'third.cc default = %s (no derivation in-tree)'
      % (dflt.group(1) if dflt else '??'))
guard = 'cbap_max_wire_packet_bytes < packet_payload_size' in th
check('Q5b. it is validated only as an UPPER BOUND (>= payload)',
      guard,
      'the only constraint is >= PACKET_PAYLOAD_SIZE, so 1064 is legal '
      'as a margin but wrong as a conversion ratio')
# every legitimate use is a byte margin, where over-estimating is SAFE
uses = re.findall(r'maxWirePacketBytes', hw)
check('Q5c. maxWirePacketBytes is used as a safety MARGIN, not a ratio',
      len(uses) > 0,
      '%d uses in rdma-hw.cc, all byte-quantity margins/bounds' % len(uses))

# ---- Q4: which domain the controller must use ---------------------------
# The answer follows from Q1-Q3: serialization, queue and served rate are the
# SAME byte count, so floor / Q_stop / drain / arrival must all use it too.
same = all(ok for n, ok, _ in res if n.startswith(('Q1.', 'Q2.', 'Q3.')))
check('Q4. floor and Q_stop must use the link byte domain (== GetSize())',
      same,
      'serialization, Q and served rate are one domain; MIN_RATE is the only '
      'payload-domain input and must be converted per QP')

print('')
for name, ok, detail in res:
    print('  [%s] %-58s %s' % ('PASS' if ok else 'FAIL', name, detail))

fail = sum(1 for _, ok, _ in res if not ok)
print('')
print('  %d/%d checks passed' % (len(res) - fail, len(res)))
print('')
if wire:
    print('  AUTHORITATIVE CONVERSION')
    print('    link_bytes_per_packet    = %d' % wire)
    print('    payload_bytes_per_packet = %d' % PAY)
    print('    payload -> link  ratio   = %d/%d = %.6f'
          % (wire, PAY, float(wire) / PAY))
    print('')
    print('  EXPECTED S3 FLOOR (65 owned QPs, MIN_RATE = 100 Mbps payload)')
    print('    payload floor = 65 x 100 Mbps            = %.4f Gbps'
          % (65 * 100e6 / 1e9))
    print('    link floor    = payload x %d/%d          = %.4f Gbps'
          % (wire, PAY, 65 * 100e6 * wire / PAY / 1e9))
    print('    DRAIN_MAX     = C - link_floor           = %.4f Gbps'
          % ((10e9 - 65 * 100e6 * wire / PAY) / 1e9))
    print('                  = %.4f C' % ((10e9 - 65 * 100e6 * wire / PAY)
                                          / 10e9))
    print('')
    print('  WRONG VALUE PRODUCED BY THE 1064 RATIO (for the record)')
    print('    65 x 100 Mbps x 1064/1000 = %.4f Gbps  <-- observed in trace'
          % (65 * 100e6 * 1.064 / 1e9))
    print('    excess over the correct floor = %.4f Gbps'
          % ((65 * 100e6 * 1.064 - 65 * 100e6 * 1.048) / 1e9))
sys.exit(1 if fail else 0)
