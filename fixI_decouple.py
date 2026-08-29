# -*- coding: utf-8 -*-
# Decouple the TX serialization recorder from CBAP-specific state.
#
# DEFECT (caught by ckpt3 dcqcn_s1, exit 2, INVALID_RECORDER_ATTACH):
#   the recorder resolved (node,if) -> link_id through cbap_link_by_id, which is
#   only populated inside ReadBopMultilinkInputs().  That function returns early
#   on `if (!RdmaHw::IsCbapMode(cc_mode))` (third.cc:763), so for CC_MODE 1
#   (DCQCN) the map is empty and every lookup fails.  The recorder is supposed to
#   be a pure physical-link observer, independent of the congestion algorithm.
#
# FIX: build an INDEPENDENT recorder link registry from selected_link_set, which
# is parsed from ROUND_TRACE_SELECTED_LINKS (third.cc:588) and is therefore
# populated for CBAP, DCQCN and flag=0 alike.
#   * authoritative physical key = (node_id, if_index)
#   * link_id = the id from the CBAP link file WHEN one is available (so CBAP
#     traces keep the same ids as before); otherwise a stable ordinal assigned
#     over the sorted (node_id, if_index) set -- deterministic, no CBAP needed
#   * cbap_link_by_id keeps its original purpose; it is only CONSULTED, never
#     required, and no CBAP initialisation is triggered for DCQCN
#
# Nothing else changes: no algorithm, rho, MIN_RATE, MAX_BOOST, queue bound,
# topology, traffic, seed or checker formula is touched.
import io
import sys

T = '/workspaces/yunxiao/simulation/scratch/third.cc'


def need(hay, needle, n=1, tag=''):
    got = hay.count(needle)
    if got != n:
        print('ANCHOR FAIL [%s]: expected %d, found %d' % (tag, n, got))
        sys.exit(2)


s = io.open(T, encoding='utf-8', errors='surrogateescape').read()

old = '''		uint32_t tx_expected = (uint32_t)selected_link_set.size();
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
			}'''
need(s, old, 1, 'attach-loop')

new = '''		uint32_t tx_expected = (uint32_t)selected_link_set.size();
		uint32_t tx_attached = 0;
		// INDEPENDENT recorder link registry.  The authoritative physical key is
		// (node_id, if_index) taken from selected_link_set, which is parsed from
		// ROUND_TRACE_SELECTED_LINKS and is populated for CBAP, DCQCN and
		// flag=0 alike.  cbap_link_by_id is CONSULTED only to keep the same
		// link ids CBAP traces already use; when it is empty (e.g. DCQCN, where
		// ReadBopMultilinkInputs returns early on !IsCbapMode) a stable ordinal
		// over the sorted (node,if) set is used instead.  No CBAP
		// initialisation is triggered here.
		uint32_t tx_ordinal = 0;
		for (set<pair<uint32_t,uint32_t> >::const_iterator sel =
				selected_link_set.begin();
				sel != selected_link_set.end(); ++sel, ++tx_ordinal){
			// Physical identity is (node,if); the id is only a label.
			uint32_t tx_link_id = tx_ordinal;
			bool tx_id_from_file = false;
			for (map<uint32_t, RdmaHw::BopMultilinkLink>::const_iterator it =
					cbap_link_by_id.begin();
					it != cbap_link_by_id.end(); ++it)
				if (it->second.nodeId == sel->first &&
						it->second.ifIndex == sel->second){
					tx_link_id = it->second.linkId;
					tx_id_from_file = true;
					break;
				}'''
s = s.replace(old, new)

# report which id source was used, so the manifest can record it
old2 = '''			tx_attached++;
			std::cout << "TX_RECORDER_ATTACHED slot=" << slot
				<< " link=" << tx_link_id
				<< " node=" << sel->first
				<< " if=" << sel->second << "\\n";'''
need(s, old2, 1, 'attach-print')
s = s.replace(old2, '''			tx_attached++;
			std::cout << "TX_RECORDER_ATTACHED slot=" << slot
				<< " link=" << tx_link_id
				<< " node=" << sel->first
				<< " if=" << sel->second
				<< " id_source=" << (tx_id_from_file ? "link_file"
					: "stable_ordinal") << "\\n";''')

io.open(T, 'w', encoding='utf-8', errors='surrogateescape').write(s)
print('recorder decoupled from CBAP state')
print('  unresolved-link fail path removed : %d (expect 0)'
      % s.count('INVALID_RECORDER_ATTACH unresolved link'))
print('  stable ordinal fallback           : %d' % s.count('tx_ordinal'))
print('  id_source reported                : %d' % s.count('id_source='))
print('  duplicate/device/count fail paths kept : %d'
      % s.count('INVALID_RECORDER_ATTACH'))
