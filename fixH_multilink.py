# -*- coding: utf-8 -*-
# Replace the single-link recorder attach block with the multi-link version.
#
# ACCEPTANCE INFRASTRUCTURE ONLY.  Touches nothing in the controller, the rate
# computation, the queue, the state machine, C, rho, MAX_BOOST, MIN_RATE,
# Q_low/Q_high/Q_red/Q_abs, ECN/PFC thresholds, topology, traffic, seed, pg, or
# any acceptance threshold.
#
# Changes:
#   1. include the ML recorder header + its static member definitions
#      (the old single-link include stays, so the old header remains compilable
#       provenance, but nothing references it any more)
#   2. replace the attach block: iterate EVERY entry of selected_link_set,
#      resolve each to its linkId from the cell's own CBAP link file, register
#      and bind a per-slot callback pair.
#   3. fail-fast: if any expected link cannot be resolved, registered or bound,
#      print INVALID_RECORDER_ATTACH and exit(2) BEFORE Simulator::Run().
import io
import sys

T = '/workspaces/yunxiao/simulation/scratch/third.cc'


def need(hay, needle, n=1, tag=''):
    got = hay.count(needle)
    if got != n:
        print('ANCHOR FAIL [%s]: expected %d, found %d' % (tag, n, got))
        sys.exit(2)


s = io.open(T, encoding='utf-8', errors='surrogateescape').read()

# ---- 1. include + statics ------------------------------------------------
if 'tx-serialization-recorder-ml.h' not in s:
    a = '#include "tx-serialization-recorder.h"'
    need(s, a, 1, 'include')
    s = s.replace(a, a + '''
// Multi-link successor.  The single-link header above is retained as
// provenance (SUPERSEDED_SINGLE_LINK_RECORDER) and is no longer referenced.
#include "tx-serialization-recorder-ml.h"''')

    a2 = 'uint64_t ns3::TxSerializationRecorder::s_recorded = 0;'
    need(s, a2, 1, 'statics')
    s = s.replace(a2, a2 + '''
FILE *ns3::TxSerializationRecorderMl::s_file = 0;
std::vector<ns3::TxSerializationRecorderMl::LinkKey>
	ns3::TxSerializationRecorderMl::s_links;
std::vector<uint64_t> ns3::TxSerializationRecorderMl::s_perLink;
uint64_t ns3::TxSerializationRecorderMl::s_windowStartNs = 0;
uint64_t ns3::TxSerializationRecorderMl::s_windowEndNs = 0;
uint64_t ns3::TxSerializationRecorderMl::s_recorded = 0;''')

# ---- 2. replace the attach block ---------------------------------------
old_start = s.index('\t// --- attach the pure-observation TX recorder (default OFF) -----------')
old_end = s.index('\tSimulator::Run();', old_start)
old_block = s[old_start:old_end]
if 'TxSerializationRecorderMl' not in old_block:
    new_block = '''	// --- attach the pure-observation TX recorder (default OFF) -----------
	// MULTI-LINK: every selected bottleneck gets its own callback pair, so a
	// dual-bottleneck scenario (S6: 84:1 and 83:1) is fully covered.  The link
	// identity is carried by the registration slot, never hardcoded and never
	// truncated to "the first bottleneck".
	//
	// Reads the PhyTxBegin/PhyTxEnd trace sources QbbNetDevice already fires.
	// Schedules nothing; mutates nothing.  An unset key leaves the run
	// bit-identical to the pre-recorder binary.
	if (!tx_serialization_trace_file.empty()){
		if (selected_link_set.empty()){
			std::cout << "INVALID_RECORDER_ATTACH no selected links\\n";
			return 2;
		}
		if (!ns3::TxSerializationRecorderMl::Open(
				tx_serialization_trace_file,
				(uint64_t)(qlen_mon_start), (uint64_t)(qlen_mon_end))){
			std::cout << "INVALID_RECORDER_ATTACH cannot open "
				<< tx_serialization_trace_file << "\\n";
			return 2;
		}
		uint32_t tx_expected = (uint32_t)selected_link_set.size();
		uint32_t tx_attached = 0;
		for (set<pair<uint32_t,uint32_t> >::const_iterator sel =
				selected_link_set.begin();
				sel != selected_link_set.end(); ++sel){
			// Resolve linkId from THIS cell's own CBAP link table; never a
			// hardcoded 84:1.
			bool found = false;
			uint32_t tx_link_id = 0;
			for (map<uint32_t, RdmaHw::BopMultilinkLink>::const_iterator it =
					cbap_link_by_id.begin();
					it != cbap_link_by_id.end(); ++it)
				if (it->second.nodeId == sel->first &&
						it->second.ifIndex == sel->second){
					tx_link_id = it->second.linkId;
					found = true;
					break;
				}
			if (!found){
				std::cout << "INVALID_RECORDER_ATTACH unresolved link "
					<< sel->first << ":" << sel->second << "\\n";
				return 2;
			}
			int slot = ns3::TxSerializationRecorderMl::Register(
				tx_link_id, sel->first, sel->second);
			if (slot < 0){
				std::cout << "INVALID_RECORDER_ATTACH duplicate link "
					<< sel->first << ":" << sel->second << "\\n";
				return 2;
			}
			Ptr<QbbNetDevice> tx_dev = DynamicCast<QbbNetDevice>(
				n.Get(sel->first)->GetDevice(sel->second));
			if (tx_dev == 0){
				std::cout << "INVALID_RECORDER_ATTACH no device "
					<< sel->first << ":" << sel->second << "\\n";
				return 2;
			}
			tx_dev->TraceConnectWithoutContext("PhyTxBegin",
				MakeBoundCallback(
					&ns3::TxSerializationRecorderMl::TxBegin,
					(uint32_t)slot));
			tx_dev->TraceConnectWithoutContext("PhyTxEnd",
				MakeBoundCallback(
					&ns3::TxSerializationRecorderMl::TxEnd,
					(uint32_t)slot));
			tx_attached++;
			std::cout << "TX_RECORDER_ATTACHED slot=" << slot
				<< " link=" << tx_link_id
				<< " node=" << sel->first
				<< " if=" << sel->second << "\\n";
		}
		if (tx_attached != tx_expected){
			std::cout << "INVALID_RECORDER_ATTACH attached=" << tx_attached
				<< " expected=" << tx_expected << "\\n";
			return 2;
		}
		std::cout << "TX_RECORDER_EXPECTED_LINKS=" << tx_expected
			<< " ATTACHED=" << tx_attached << "\\n";
		fflush(stdout);
	}
'''
    s = s[:old_start] + new_block + s[old_end:]

# ---- 3. close the ML recorder after the run ---------------------------
if 'TxSerializationRecorderMl::Close' not in s:
    a = '\tns3::TxSerializationRecorder::Close();'
    need(s, a, 1, 'close')
    s = s.replace(a, a + '\n\tns3::TxSerializationRecorderMl::Close();')

io.open(T, 'w', encoding='utf-8', errors='surrogateescape').write(s)
print('multi-link recorder wired')
print('  ML include        : %d' % s.count('tx-serialization-recorder-ml.h'))
print('  ML statics        : %d' % s.count('TxSerializationRecorderMl::s_'))
print('  Register calls    : %d' % s.count('TxSerializationRecorderMl::Register'))
print('  per-slot binds    : %d'
      % (s.count('TxSerializationRecorderMl::TxBegin')
         + s.count('TxSerializationRecorderMl::TxEnd')))
print('  fail-fast exits   : %d' % s.count('INVALID_RECORDER_ATTACH'))
print('  size()==1 guard   : %d (expect 0)'
      % s.count('selected_link_set.size() == 1 &&'))
