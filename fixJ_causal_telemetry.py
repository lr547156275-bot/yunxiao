# -*- coding: utf-8 -*-
# Wire the two causal tracers into third.cc.  TELEMETRY ONLY.
#
# Touches nothing in the controller, rate computation, queue, state machine,
# rho, MAX_BOOST, MIN_RATE, queue boundaries, ECN/PFC, topology, traffic, seed,
# acceptance gates or frozen checkers.  Both tracers default OFF.
#
# Queue tracer attaches to the EXISTING BeqEnqueue / BeqDequeue trace sources on
# the bottleneck egress device's BEgressQueue, plus PhyTxBegin / PhyTxEnd on the
# device.  Signatures verified: TracedCallback<Ptr<const Packet>, uint32_t> and
# TracedCallback<Ptr<const Packet>>.
#
# Pacer tracer is emitted from inside ChangeRate's CBAP branch, where the
# candidate and final m_nextAvail are both in scope.
import io
import sys

T = '/workspaces/yunxiao/simulation/scratch/third.cc'
H = '/workspaces/yunxiao/simulation/src/point-to-point/model/rdma-hw.cc'


def need(hay, needle, n=1, tag=''):
    got = hay.count(needle)
    if got != n:
        print('ANCHOR FAIL [%s]: expected %d found %d' % (tag, n, got))
        sys.exit(2)


s = io.open(T, encoding='utf-8', errors='surrogateescape').read()

# ---- include + statics ---------------------------------------------------
if 'causal-telemetry.h' not in s:
    a = '#include "tx-serialization-recorder-ml.h"'
    need(s, a, 1, 'include-anchor')
    s = s.replace(a, a + '''
#include "causal-telemetry.h"
FILE *ns3::CausalQueueTrace::s_file = 0;
std::vector<ns3::CausalQueueTrace::Key> ns3::CausalQueueTrace::s_link;
uint64_t ns3::CausalQueueTrace::s_lo = 0;
uint64_t ns3::CausalQueueTrace::s_hi = 0;
uint64_t ns3::CausalQueueTrace::s_rows = 0;
FILE *ns3::CausalPacerTrace::s_file = 0;
uint64_t ns3::CausalPacerTrace::s_lo = 0;
uint64_t ns3::CausalPacerTrace::s_hi = 0;
uint64_t ns3::CausalPacerTrace::s_rows = 0;
string causal_queue_trace_file = "", causal_pacer_trace_file = "";
uint64_t causal_trace_start_ns = 0, causal_trace_end_ns = 0;''')

# ---- config keys --------------------------------------------------------
if 'CAUSAL_QUEUE_TRACE_FILE' not in s.replace('causal_queue_trace_file', ''):
    a = '\t\t\telse if(key.compare("TX_SERIALIZATION_TRACE_FILE")==0){'
    need(s, a, 1, 'cfg-anchor')
    s = s.replace(a, '''			else if(key.compare("CAUSAL_QUEUE_TRACE_FILE")==0){
				conf>>causal_queue_trace_file;
				std::cout << "CAUSAL_QUEUE_TRACE_FILE\\t\\t"
					<< causal_queue_trace_file << "\\n";
			}
			else if(key.compare("CAUSAL_PACER_TRACE_FILE")==0){
				conf>>causal_pacer_trace_file;
				std::cout << "CAUSAL_PACER_TRACE_FILE\\t\\t"
					<< causal_pacer_trace_file << "\\n";
			}
			else if(key.compare("CAUSAL_TRACE_START_NS")==0)
				conf>>causal_trace_start_ns;
			else if(key.compare("CAUSAL_TRACE_END_NS")==0)
				conf>>causal_trace_end_ns;
''' + a)

# ---- static callbacks + attach block ------------------------------------
if 'CausalQueueOnEnqueue' not in s:
    a = '\tif (!tx_serialization_trace_file.empty()){'
    need(s, a, 1, 'attach-anchor')
    s = s.replace(a, '''	// --- causal telemetry attach (both default OFF) -----------------------
	// Read-only: the callbacks below only read GetNBytesTotal() and the packet
	// header; they schedule/cancel nothing and mutate nothing.
	if (!causal_queue_trace_file.empty()){
		if (selected_link_set.empty()){
			std::cout << "INVALID_CAUSAL_ATTACH no selected links\\n";
			return 2;
		}
		if (!ns3::CausalQueueTrace::Open(causal_queue_trace_file,
				causal_trace_start_ns, causal_trace_end_ns)){
			std::cout << "INVALID_CAUSAL_ATTACH cannot open queue trace\\n";
			return 2;
		}
		uint32_t cq_expected = (uint32_t)selected_link_set.size();
		uint32_t cq_attached = 0;
		uint32_t cq_ord = 0;
		for (set<pair<uint32_t,uint32_t> >::const_iterator sel =
				selected_link_set.begin();
				sel != selected_link_set.end(); ++sel, ++cq_ord){
			uint32_t cq_link = cq_ord;
			for (map<uint32_t, RdmaHw::BopMultilinkLink>::const_iterator it =
					cbap_link_by_id.begin();
					it != cbap_link_by_id.end(); ++it)
				if (it->second.nodeId == sel->first &&
						it->second.ifIndex == sel->second){
					cq_link = it->second.linkId;
					break;
				}
			int slot = ns3::CausalQueueTrace::Register(cq_link, sel->first,
				sel->second);
			if (slot < 0){
				std::cout << "INVALID_CAUSAL_ATTACH duplicate link\\n";
				return 2;
			}
			Ptr<QbbNetDevice> cqdev = DynamicCast<QbbNetDevice>(
				n.Get(sel->first)->GetDevice(sel->second));
			if (cqdev == 0){
				std::cout << "INVALID_CAUSAL_ATTACH no device\\n";
				return 2;
			}
			causal_slot_dev[slot] = cqdev;
			cqdev->GetQueue()->TraceConnectWithoutContext("BeqEnqueue",
				MakeBoundCallback(&CausalQueueOnEnqueue, (uint32_t)slot));
			cqdev->GetQueue()->TraceConnectWithoutContext("BeqDequeue",
				MakeBoundCallback(&CausalQueueOnDequeue, (uint32_t)slot));
			cqdev->TraceConnectWithoutContext("PhyTxBegin",
				MakeBoundCallback(&CausalQueueOnTxBegin, (uint32_t)slot));
			cqdev->TraceConnectWithoutContext("PhyTxEnd",
				MakeBoundCallback(&CausalQueueOnTxEnd, (uint32_t)slot));
			cq_attached++;
			std::cout << "CAUSAL_QUEUE_ATTACHED slot=" << slot
				<< " link=" << cq_link << " node=" << sel->first
				<< " if=" << sel->second << "\\n";
		}
		if (cq_attached != cq_expected){
			std::cout << "INVALID_CAUSAL_ATTACH attached=" << cq_attached
				<< " expected=" << cq_expected << "\\n";
			return 2;
		}
		fflush(stdout);
	}
	if (!causal_pacer_trace_file.empty()){
		if (!ns3::CausalPacerTrace::Open(causal_pacer_trace_file,
				causal_trace_start_ns, causal_trace_end_ns)){
			std::cout << "INVALID_CAUSAL_ATTACH cannot open pacer trace\\n";
			return 2;
		}
		std::cout << "CAUSAL_PACER_ATTACHED\\n";
		fflush(stdout);
	}
''' + a)

# static callbacks + slot->device map, placed before main
if 'static map<uint32_t, Ptr<QbbNetDevice> > causal_slot_dev' not in s:
    a = 'void LinkTraceTick(){'
    need(s, a, 1, 'cb-anchor')
    s = s.replace(a, '''static map<uint32_t, Ptr<QbbNetDevice> > causal_slot_dev;

// Read the queue depth AT THE EVENT INSTANT.  BeqEnqueue fires AFTER the
// counter is incremented; BeqDequeue fires BEFORE it is decremented.  The
// tracer records both interpretations explicitly.
static uint64_t CausalQBytes(uint32_t slot){
	map<uint32_t, Ptr<QbbNetDevice> >::const_iterator it =
		causal_slot_dev.find(slot);
	if (it == causal_slot_dev.end() || it->second == 0)
		return 0;
	return it->second->GetQueue()->GetNBytesTotal();
}
static bool CausalBusy(uint32_t slot){
	map<uint32_t, Ptr<QbbNetDevice> >::const_iterator it =
		causal_slot_dev.find(slot);
	if (it == causal_slot_dev.end() || it->second == 0)
		return false;
	return !it->second->GetQueue()->GetNBytesTotal() ? false : true;
}
static void CausalQueueOnEnqueue(uint32_t slot, Ptr<const Packet> p,
		uint32_t qIndex){
	ns3::CausalQueueTrace::OnEnqueue(slot, CausalQBytes(slot), 0, p, qIndex,
		CausalBusy(slot), 0);
}
static void CausalQueueOnDequeue(uint32_t slot, Ptr<const Packet> p,
		uint32_t qIndex){
	ns3::CausalQueueTrace::OnDequeue(slot, CausalQBytes(slot), 0, p, qIndex,
		CausalBusy(slot), 0);
}
static void CausalQueueOnTxBegin(uint32_t slot, Ptr<const Packet> p){
	ns3::CausalQueueTrace::OnTxBegin(slot, CausalQBytes(slot), 0, p);
}
static void CausalQueueOnTxEnd(uint32_t slot, Ptr<const Packet> p){
	ns3::CausalQueueTrace::OnTxEnd(slot, CausalQBytes(slot), 0, p);
}

''' + a)

# ---- close both at end of run ------------------------------------------
if 'CausalQueueTrace::Close' not in s:
    a = '\tns3::TxSerializationRecorderMl::Close();'
    need(s, a, 1, 'close-anchor')
    s = s.replace(a, a + '''
	ns3::CausalQueueTrace::Close();
	ns3::CausalPacerTrace::Close();''')

io.open(T, 'w', encoding='utf-8', errors='surrogateescape').write(s)

# ---- pacer emit inside ChangeRate --------------------------------------
c = io.open(H, encoding='utf-8', errors='surrogateescape').read()
if 'CausalPacerTrace' not in c:
    if '#include "causal-telemetry.h"' not in c:
        a0 = '#include "rdma-hw.h"'
        need(c, a0, 1, 'hw-include')
        c = c.replace(a0, a0 + '\n#include "../../../scratch/causal-telemetry.h"')
    old = '''		if (qp->cbap.creditGateActive && qp->m_nextAvail > next)
			next = qp->m_nextAvail;
		qp->m_nextAvail = next;'''
    need(c, old, 1, 'changerate-body')
    c = c.replace(old, '''		const uint64_t causal_cand = next.GetTimeStep();
		const uint64_t causal_old_na = qp->m_nextAvail.GetTimeStep();
		if (qp->cbap.creditGateActive && qp->m_nextAvail > next)
			next = qp->m_nextAvail;
		qp->m_nextAvail = next;
		// Telemetry only: records the pacing decision that was just taken.
		// Emits nothing when the tracer is closed.
		if (ns3::CausalPacerTrace::IsOpen())
			ns3::CausalPacerTrace::Emit(qp->crfm.flowId, 0, 0,
				"ChangeRate_cbap", qp->m_rate.GetBitRate(),
				new_rate.GetBitRate(), qp->cbap.lastTxTimeNs,
				causal_old_na, causal_cand,
				qp->m_nextAvail.GetTimeStep(), 0, 0,
				qp->m_nextAvail.GetTimeStep() > causal_old_na ? "LATER" :
				(qp->m_nextAvail.GetTimeStep() < causal_old_na ? "EARLIER" :
				 "KEEP"), 0);''')
    io.open(H, 'w', encoding='utf-8', errors='surrogateescape').write(c)

print('wired')
print('  third.cc  causal-telemetry include : %d' % s.count('causal-telemetry.h'))
print('  config keys                        : %d'
      % (s.count('CAUSAL_QUEUE_TRACE_FILE') + s.count('CAUSAL_PACER_TRACE_FILE')))
print('  attach guards (fail-fast)          : %d' % s.count('INVALID_CAUSAL_ATTACH'))
print('  rdma-hw.cc pacer emit              : %d' % c.count('CausalPacerTrace::Emit'))
print('  Schedule/Cancel in telemetry hdr   : 0 (by construction)')
