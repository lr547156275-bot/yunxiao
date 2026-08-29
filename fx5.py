import io

# `config.packetPayloadBytes` at third.cc:3065 targets a DIFFERENT config
# struct (BOP's), not CbapConfig. The controller needs the payload size in
# CbapConfig to do the wire<->payload conversion, so declare it there and set
# it alongside the other qc* fields.
ph = '/work/simulation/src/point-to-point/model/rdma-hw.h'
h = io.open(ph, encoding='utf-8', errors='surrogateescape').read()
if h.count('qcPayloadPacketBytes') == 0:
    a = '\t\tuint64_t qcSafetyMarginBytes; // M_safe, from the measured residual'
    assert h.count(a) == 1, ('anchor', h.count(a))
    h = h.replace(a, a + '\n'
                  '\t\t// PACKET_PAYLOAD_SIZE. Paired with qcOnWirePacketBytes to\n'
                  '\t\t// convert between the payload domain (MIN_RATE, sender\n'
                  '\t\t// pacing) and the wire domain (queue bytes, link rate).\n'
                  '\t\tuint64_t qcPayloadPacketBytes;')
    b = '\t\t\t  qcOnWirePacketBytes(0), qcSafetyMarginBytes(0),'
    assert h.count(b) == 1, ('init', h.count(b))
    h = h.replace(b, '\t\t\t  qcOnWirePacketBytes(0), qcSafetyMarginBytes(0),\n'
                     '\t\t\t  qcPayloadPacketBytes(0),')
    io.open(ph, 'w', encoding='utf-8', errors='surrogateescape').write(h)

pc = '/work/simulation/src/point-to-point/model/rdma-hw.cc'
c = io.open(pc, encoding='utf-8', errors='surrogateescape').read()
old = '''		const uint64_t payloadBytes = s_cbapConfig.packetPayloadBytes > 0 ?
			s_cbapConfig.packetPayloadBytes : 1000;'''
assert c.count(old) == 1, ('use', c.count(old))
c = c.replace(old, '''		const uint64_t payloadBytes =
			s_cbapConfig.qcPayloadPacketBytes > 0 ?
			s_cbapConfig.qcPayloadPacketBytes : 1000;''')
io.open(pc, 'w', encoding='utf-8', errors='surrogateescape').write(c)

p = '/work/simulation/scratch/third.cc'
s = io.open(p, encoding='utf-8', errors='surrogateescape').read()
if s.count('config.qcPayloadPacketBytes') == 0:
    a2 = '\tconfig.qcOnWirePacketBytes = cbap_max_wire_packet_bytes;'
    assert s.count(a2) == 1, ('push', s.count(a2))
    s = s.replace(a2, a2 + '\n'
                  '\tconfig.qcPayloadPacketBytes = packet_payload_size;')
    io.open(p, 'w', encoding='utf-8', errors='surrogateescape').write(s)

print("qcPayloadPacketBytes declared=%d used=%d pushed=%d"
      % (h.count('qcPayloadPacketBytes'), c.count('qcPayloadPacketBytes'),
         s.count('config.qcPayloadPacketBytes')))
