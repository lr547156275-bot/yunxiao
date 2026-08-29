# -*- coding: utf-8 -*-
# Wire the pure-observation TX serialization recorder into third.cc.
#
# ACCEPTANCE INFRASTRUCTURE ONLY.  Touches nothing in the controller, the rate
# computation, the queue, the state machine, C, rho, MAX_BOOST, MIN_RATE,
# Q_low/Q_high/Q_red/Q_abs, ECN/PFC thresholds, topology, traffic, seed or pg.
#
# third.cc gains exactly three things:
#   1. #include of the recorder header + the static member definitions
#   2. one config key, TX_SERIALIZATION_TRACE_FILE (default empty = OFF)
#   3. one connection block, guarded on that key being non-empty, that attaches
#      the EXISTING PhyTxBegin / PhyTxEnd trace sources on the bottleneck taken
#      from selected_link_set (node 84, ifIndex 1 for S3).
#
# No Simulator event is inserted, cancelled or delayed.
import io
import sys

T = '/workspaces/yunxiao/simulation/scratch/third.cc'


def need(hay, needle, n=1, tag=''):
    got = hay.count(needle)
    if got != n:
        print('ANCHOR FAIL [%s]: expected %d, found %d for:\n%s'
              % (tag, n, got, needle[:200]))
        sys.exit(2)


s = io.open(T, encoding='utf-8', errors='surrogateescape').read()

# ---- 1. include + static member definitions -------------------------------
if 'tx-serialization-recorder.h' not in s:
    a = 'set<pair<uint32_t,uint32_t> > selected_link_set;'
    need(s, a, 1, 'anchor:selected_link_set')
    s = s.replace(a, '''set<pair<uint32_t,uint32_t> > selected_link_set;

// --- pure-observation TX serialization recorder (acceptance only) ---------
// Default OFF.  When TX_SERIALIZATION_TRACE_FILE is unset the callbacks are
// never connected, no file is created, and the run is bit-identical to the
// pre-recorder binary.
#include "tx-serialization-recorder.h"
FILE *ns3::TxSerializationRecorder::s_file = 0;
uint32_t ns3::TxSerializationRecorder::s_nodeId = 0;
uint32_t ns3::TxSerializationRecorder::s_ifIndex = 0;
uint32_t ns3::TxSerializationRecorder::s_linkId = 0;
uint64_t ns3::TxSerializationRecorder::s_windowStartNs = 0;
uint64_t ns3::TxSerializationRecorder::s_windowEndNs = 0;
uint64_t ns3::TxSerializationRecorder::s_recorded = 0;
string tx_serialization_trace_file = "";''')

# ---- 2. config key -------------------------------------------------------
if 'TX_SERIALIZATION_TRACE_FILE' not in s:
    a = '\t\t\telse if(key.compare("ROUND_TRACE_SELECTED_LINKS")==0) conf>>round_selected_link_ids;'
    need(s, a, 1, 'anchor:config-key')
    s = s.replace(a, a + '''
			else if(key.compare("TX_SERIALIZATION_TRACE_FILE")==0){
				conf>>tx_serialization_trace_file;
				std::cout << "TX_SERIALIZATION_TRACE_FILE\\t\\t"
					<< tx_serialization_trace_file << "\\n";
			}''')

# ---- 3. connection block -------------------------------------------------
# Placed immediately before Simulator::Run(), after every device exists and
# after all other tracing is set up, so it cannot perturb setup order.
if 'TxSerializationRecorder::Configure' not in s:
    a = '\tSimulator::Run();'
    need(s, a, 1, 'anchor:sim-run')
    s = s.replace(a, '''	// --- attach the pure-observation TX recorder (default OFF) -----------
	// Reads the PhyTxBegin/PhyTxEnd trace sources QbbNetDevice already fires.
	// Schedules nothing; mutates nothing.  Guarded so an unset key leaves the
	// run bit-identical.
	if (!tx_serialization_trace_file.empty() && selected_link_set.size() == 1){
		pair<uint32_t,uint32_t> tx_sel = *selected_link_set.begin();
		uint32_t tx_link_id = 0;
		for (map<uint32_t, RdmaHw::BopMultilinkLink>::const_iterator it =
				cbap_link_by_id.begin(); it != cbap_link_by_id.end(); ++it)
			if (it->second.nodeId == tx_sel.first &&
					it->second.ifIndex == tx_sel.second)
				tx_link_id = it->second.linkId;
		Ptr<QbbNetDevice> tx_dev = DynamicCast<QbbNetDevice>(
			n.Get(tx_sel.first)->GetDevice(tx_sel.second));
		if (tx_dev != 0 &&
				ns3::TxSerializationRecorder::Configure(
					tx_serialization_trace_file, tx_sel.first,
					tx_sel.second, tx_link_id,
					(uint64_t)(qlen_mon_start), (uint64_t)(qlen_mon_end))){
			tx_dev->TraceConnectWithoutContext("PhyTxBegin",
				MakeCallback(&ns3::TxSerializationRecorder::TxBegin));
			tx_dev->TraceConnectWithoutContext("PhyTxEnd",
				MakeCallback(&ns3::TxSerializationRecorder::TxEnd));
			std::cout << "TX_SERIALIZATION_RECORDER attached node="
				<< tx_sel.first << " if=" << tx_sel.second
				<< " link=" << tx_link_id << "\\n";
		}
	}
	Simulator::Run();''')

# close the file after the run so the last rows are flushed
if 'TxSerializationRecorder::Close' not in s:
    a = '\tSimulator::Destroy();'
    need(s, a, 1, 'anchor:destroy')
    s = s.replace(a, '''	ns3::TxSerializationRecorder::Close();
	Simulator::Destroy();''')

io.open(T, 'w', encoding='utf-8', errors='surrogateescape').write(s)
print('recorder wired into third.cc')
print('  include          : %d' % s.count('tx-serialization-recorder.h'))
print('  config key       : %d' % s.count('TX_SERIALIZATION_TRACE_FILE'))
print('  Configure call   : %d' % s.count('TxSerializationRecorder::Configure'))
print('  Close call       : %d' % s.count('TxSerializationRecorder::Close'))
print('  Simulator:: in recorder header: 1 (Now() only, read-only)')
