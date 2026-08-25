# -*- coding: utf-8 -*-
# v2 round-3 patch, two independent fixes, both default-OFF (v1 byte-identical,
# proven by twin regression):
#
# 1. TX_TIME_ROUND_NS: per-packet tx time is computed as
#    Seconds(CalculateTxTime()) -- a double whose ns conversion FLOORS.  With
#    integer-exact packet times (wire 1000B -> 800/40/20ns) the double lands
#    just below the integer and every packet goes out 1ns early: +0.125% rate
#    at 10G, +2.6% at 200G, +5.3% at 400G (measured 799/39/19ns in preflight
#    round 2).  Flag ON rounds to the nearest integer ns at BOTH physics
#    sites: the qbb device serialization and the QP pacing timer.
#    (CBAP exact-grant pacing already uses integer CbapPacketGapNs.)
#
# 2. CBAP_TX_RECORDS_MAX: RecordCbapTxEvent pushes one ~160B record per packet
#    into the in-memory s_cbapTxRecords vector; the existing
#    txTraceTrackingPackets cap only applies to TRACKING/RECOVERY/STARTUP
#    phases, so a steady-state background flow grows it without bound.  At
#    400G that is ~4.6M packets by t=121ms -> ~1.5GB vector -> doubling
#    realloc -> std::bad_alloc (heff_400g round-2 crash).  Flag >0 hard-caps
#    the vector (drops counted); 0 = unlimited legacy.
import io
import sys

HWH = '/work/simulation/src/point-to-point/model/rdma-hw.h'
HWC = '/work/simulation/src/point-to-point/model/rdma-hw.cc'
QBB = '/work/simulation/src/point-to-point/model/qbb-net-device.cc'
T = '/work/simulation/scratch/third.cc'
src = {}
for tag, p in (('h', HWH), ('c', HWC), ('q', QBB), ('t', T)):
    src[tag] = io.open(p, encoding='utf-8', errors='surrogateescape').read()
if 'txRecordsMax' in src['h']:
    print('already applied')
    sys.exit(0)

BSN = chr(92) + 'n'
BST = chr(92) + 't'
edits = []


def E(tag, w, old, new):
    edits.append((tag, w, old, new))


# --- rdma-hw.h: config field + ctor default -------------------------------
E('h-field', 'h',
  '\t\tuint32_t txTraceTrackingPackets;',
  '\t\tuint32_t txTraceTrackingPackets;\n'
  '\t\t// v2: hard cap on the in-memory CBAP tx-record vector\n'
  '\t\t// (0 = unlimited legacy behaviour)\n'
  '\t\tuint64_t txRecordsMax;')
E('h-ctor', 'h',
  'sbaWireDomainPlanning(false),',
  'sbaWireDomainPlanning(false), txRecordsMax(0),')

# --- rdma-hw.cc: globals + record cap + pacing rounding --------------------
E('c-globals', 'c',
  'std::vector<RdmaHw::CbapTxRecord> RdmaHw::s_cbapTxRecords;',
  'std::vector<RdmaHw::CbapTxRecord> RdmaHw::s_cbapTxRecords;\n'
  'uint64_t g_cbapTxRecordsDropped = 0;\n'
  '// TX_TIME_ROUND_NS (v2): round per-packet tx time to the nearest ns at\n'
  '// both physics sites (device serialization + QP pacing).  Default false\n'
  '// keeps the legacy double-floor behaviour byte-identical.\n'
  'bool g_txTimeRoundNs = false;')
E('c-cap', 'c',
  '\tCbapTxRecord record = {};',
  '\tif (s_cbapConfig.txRecordsMax > 0 &&\n'
  '\t\t\ts_cbapTxRecords.size() >= s_cbapConfig.txRecordsMax){\n'
  '\t\tg_cbapTxRecordsDropped++;\n'
  '\t\treturn;\n'
  '\t}\n'
  '\tCbapTxRecord record = {};')
E('c-pacing', 'c',
  '\t}else\n'
  '\t\tsendingTime = interframeGap +\n'
  '\t\t\tSeconds(DataRate(effectiveRate).CalculateTxTime(pkt_size));',
  '\t}else if (g_txTimeRoundNs){\n'
  '\t\tsendingTime = interframeGap + NanoSeconds((uint64_t)(\n'
  '\t\t\tDataRate(effectiveRate).CalculateTxTime(pkt_size) * 1e9 + 0.5));\n'
  '\t}else\n'
  '\t\tsendingTime = interframeGap +\n'
  '\t\t\tSeconds(DataRate(effectiveRate).CalculateTxTime(pkt_size));')

# --- qbb-net-device.cc: device serialization rounding ----------------------
E('q-serialize', 'q',
  '\t\tTime txTime = Seconds(m_bps.CalculateTxTime(p->GetSize()));',
  '\t\textern bool g_txTimeRoundNs;   // defined in rdma-hw.cc\n'
  '\t\tTime txTime = Seconds(m_bps.CalculateTxTime(p->GetSize()));\n'
  '\t\tif (g_txTimeRoundNs)\n'
  '\t\t\ttxTime = NanoSeconds((uint64_t)(\n'
  '\t\t\t\tm_bps.CalculateTxTime(p->GetSize()) * 1e9 + 0.5));')

# --- third.cc: globals, parse, assign --------------------------------------
E('t-globals', 't',
  'uint32_t sba_wire_domain_planning = 0;   // v2 campaigns only, default 0',
  'uint32_t sba_wire_domain_planning = 0;   // v2 campaigns only, default 0\n'
  'uint32_t tx_time_round_ns = 0;           // v2: exact integer-ns tx times\n'
  'uint64_t cbap_tx_records_max = 0;        // v2: cap in-memory tx records\n'
  'namespace ns3 { extern bool g_txTimeRoundNs; }')
E('t-parse', 't',
  '\t\t\telse if(key.compare("SBA_WIRE_DOMAIN_PLANNING")==0){',
  '\t\t\telse if(key.compare("TX_TIME_ROUND_NS")==0){\n'
  '\t\t\t\tconf>>tx_time_round_ns;\n'
  '\t\t\t\tstd::cout << "TX_TIME_ROUND_NS' + BST + BST + '"\n'
  '\t\t\t\t\t<< tx_time_round_ns << "' + BSN + '";\n'
  '\t\t\t}\n'
  '\t\t\telse if(key.compare("CBAP_TX_RECORDS_MAX")==0){\n'
  '\t\t\t\tconf>>cbap_tx_records_max;\n'
  '\t\t\t\tstd::cout << "CBAP_TX_RECORDS_MAX' + BST + BST + '"\n'
  '\t\t\t\t\t<< cbap_tx_records_max << "' + BSN + '";\n'
  '\t\t\t}\n'
  '\t\t\telse if(key.compare("SBA_WIRE_DOMAIN_PLANNING")==0){')
E('t-assign', 't',
  '\tconfig.sbaWireDomainPlanning = (sba_wire_domain_planning != 0);',
  '\tconfig.sbaWireDomainPlanning = (sba_wire_domain_planning != 0);\n'
  '\tconfig.txRecordsMax = cbap_tx_records_max;\n'
  '\tg_txTimeRoundNs = (tx_time_round_ns != 0);')

bad = 0
for tag, w, old, new in edits:
    n = src[w].count(old)
    print('%-12s %s count=%d %s' % (tag, w, n, 'OK' if n == 1 else 'FAIL'))
    if n != 1:
        bad += 1
if bad:
    print('ANCHOR FAIL -- nothing written')
    sys.exit(2)
for tag, w, old, new in edits:
    src[w] = src[w].replace(old, new, 1)
io.open(HWH, 'w', encoding='utf-8', errors='surrogateescape').write(src['h'])
io.open(HWC, 'w', encoding='utf-8', errors='surrogateescape').write(src['c'])
io.open(QBB, 'w', encoding='utf-8', errors='surrogateescape').write(src['q'])
io.open(T, 'w', encoding='utf-8', errors='surrogateescape').write(src['t'])
print('round-3 patch applied (both flags default OFF = v1 byte-identical)')
