# -*- coding: utf-8 -*-
# Wire the send-opportunity tracer.  TELEMETRY ONLY, DEFAULT OFF.
#
# Touches no control logic.  Every insertion is either a pure emit or a
# read-only capture of a value the surrounding code already computed.  No
# condition is changed, no branch is added or removed, no field is written.
# Identical instrumentation for CBAP and DCQCN -- the emit sites are in
# QbbNetDevice / RdmaEgressQueue, which both algorithms share.
#
# Does NOT modify: rho, MAX_BOOST, MIN_RATE, Q_low/Q_high/Q_red/Q_abs, ECN, PFC,
# ShouldSendCN, CNP handling, HandoffCbapSbaFlow, topology, traffic, seeds,
# routing, acceptance gates, or any frozen checker.
import io
import sys

QBB = '/work/simulation/src/point-to-point/model/qbb-net-device.cc'
QBBH = '/work/simulation/src/point-to-point/model/qbb-net-device.h'
T = '/work/simulation/scratch/third.cc'


def need(hay, needle, n=1, tag=''):
    got = hay.count(needle)
    if got != n:
        print('ANCHOR FAIL [%s]: expected %d found %d' % (tag, n, got))
        sys.exit(2)


# ======================================================================== hdr
h = io.open(QBBH, encoding='utf-8', errors='surrogateescape').read()
if 'SenderOppTrace' not in h:
    a = 'class QbbNetDevice : public PointToPointNetDevice'
    need(h, a, 1, 'qbb-h-class')
    h = h.replace('#include "ns3/event-id.h"',
                  '#include "ns3/event-id.h"\n'
                  '#include "../../../scratch/sender-opportunity-telemetry.h"', 1)
    # NOT written yet -- every file is written only after all anchors in all
    # three files have matched, so a late anchor failure cannot leave a
    # partially-patched tree (which is exactly what happened on the first run).

# ======================================================================== cc
c = io.open(QBB, encoding='utf-8', errors='surrogateescape').read()

# ---- statics (owned by the library that references them) -----------------
if 'ns3::SenderOppTrace::s_file' not in c:
    a = 'namespace ns3 {'
    need(c, a, 1, 'qbb-ns-open')
    c = c.replace(a, a + '''
// Owned here: qbb-net-device.cc is inside libns3-point-to-point, which
// references these symbols.  Telemetry only.
FILE *SenderOppTrace::s_file = 0;
std::vector<SenderOppTrace::Key> SenderOppTrace::s_link;
std::string SenderOppTrace::s_algo = "";
uint64_t SenderOppTrace::s_lo = 0;
uint64_t SenderOppTrace::s_hi = 0;
uint64_t SenderOppTrace::s_rows = 0;
uint64_t SenderOppTrace::s_opp = 0;
''', 1)

# ---- GetNextQindex: per-QP reason capture -------------------------------
# The scan's decisions are captured WITHOUT changing them: the same predicates
# are re-evaluated read-only into a side vector, and the emit happens after the
# original loop has already produced its result.
# All .cc edits happen in one pass against the frozen file.  If any anchor fails
# the script exits before writing, so the tree is never left half-patched: the
# write below is the single commit point.
old_scan = '''	int RdmaEgressQueue::GetNextQindex(bool paused[]){
		bool found = false;
		uint32_t qIndex;
		if (!paused[ack_q_idx] && m_ackQ->GetNPackets() > 0)
			return -1;'''
need(c, old_scan, 1, 'getnextqindex-head')
c = c.replace(old_scan, '''	// Telemetry: per-QP outcome of the most recent scan.  Filled read-only by
	// GetNextQindex, consumed by DequeueAndTransmit, which owns the port
	// identity needed to emit.  Cleared at the start of every scan so a stale
	// entry can never be attributed to a later opportunity.
	std::vector<RdmaEgressQueue::OppRec> RdmaEgressQueue::s_oppRec;
	int RdmaEgressQueue::s_oppSelected = -1024;

	int RdmaEgressQueue::GetNextQindex(bool paused[]){
		bool found = false;
		uint32_t qIndex;
		s_oppRec.clear();
		s_oppSelected = -1024;
		const bool trace_opp = SenderOppTrace::IsOpen();
		if (!paused[ack_q_idx] && m_ackQ->GetNPackets() > 0)
			return -1;''', 1)

old_body = '''			if (!paused[qp->m_pg] && !qp->cbap.zeroGrantPaused &&
					qp->GetBytesLeft() > 0 && !qp->IsWinBound()){
				if (m_qpGrp->Get(idx)->m_nextAvail.GetTimeStep() > Simulator::Now().GetTimeStep()) //not available now
					continue;
				res = idx;
				break;
			}else if (qp->IsFinished()){
				min_finish_id = idx < min_finish_id ? idx : min_finish_id;
			}'''
need(c, old_body, 1, 'getnextqindex-body')
c = c.replace(old_body, '''			if (trace_opp){
				// Read-only replay of the same predicates, in the same order,
				// purely to label why this QP was or was not usable.  Assigns
				// nothing and cannot alter the scan below.
				OppRec r;
				r.idx = idx;
				r.nextAvail = qp->m_nextAvail.GetTimeStep();
				r.bytesLeft = qp->GetBytesLeft();
				r.rate = qp->m_rate.GetBitRate();
				r.lastTx = qp->cbap.lastTxTimeNs;
				r.flowId = qp->crfm.flowId;
				r.batchId = qp->cbap.batchId;
				const bool fin = qp->IsFinished();
				const bool zgp = qp->cbap.zeroGrantPaused;
				const bool pau = paused[qp->m_pg];
				const bool win = qp->IsWinBound();
				if (fin)
					r.reason = "FLOW_FINISHED";
				else if (zgp)
					r.reason = "HANDOFF_PENDING";
				else if (pau || win || r.bytesLeft == 0)
					r.reason = "NO_PACKET";
				else if (r.nextAvail > Simulator::Now().GetTimeStep())
					r.reason = "NEXT_AVAIL_FUTURE";
				else
					r.reason = "ELIGIBLE";     // refined later: SENT or
					                           // ELIGIBLE_NOT_SELECTED
				s_oppRec.push_back(r);
			}
			if (!paused[qp->m_pg] && !qp->cbap.zeroGrantPaused &&
					qp->GetBytesLeft() > 0 && !qp->IsWinBound()){
				if (m_qpGrp->Get(idx)->m_nextAvail.GetTimeStep() > Simulator::Now().GetTimeStep()) //not available now
					continue;
				res = idx;
				break;
			}else if (qp->IsFinished()){
				min_finish_id = idx < min_finish_id ? idx : min_finish_id;
			}''', 1)

# record the selected index after the finished-QP compaction has renumbered it
old_ret = '''			qps.resize(nxt);
		}
		return res;
	}'''
need(c, old_ret, 1, 'getnextqindex-ret')
c = c.replace(old_ret, '''			qps.resize(nxt);
		}
		s_oppSelected = res;
		return res;
	}''', 1)

# ---- DequeueAndTransmit: opportunity-level emits ------------------------
old_busy = '''		if (!m_linkUp) return; // if link is down, return
		if (m_txMachineState == BUSY) return;	// Quit if channel busy'''
need(c, old_busy, 1, 'dqt-busy')
c = c.replace(old_busy, '''		if (!m_linkUp) return; // if link is down, return
		if (m_txMachineState == BUSY){
			// Telemetry: a send opportunity that the serializer refused.
			if (SenderOppTrace::IsOpen() && SenderOppTrace::InWindow()){
				const int slot = SenderOppTrace::SlotOf(m_node->GetId(),
					m_ifIndex);
				if (slot >= 0)
					SenderOppTrace::Emit(slot,
						SenderOppTrace::NextOpportunityId(), "OPPORTUNITY",
						"NIC_BUSY", 0, 0, 0, 0,
						m_currentPkt ? m_currentPkt->GetUid() : 0,
						0, 0, 0, 0,
						m_currentPkt ? m_currentPkt->GetSize() : 0,
						0, 0, 0, 0, 0, 0, -1024);
			}
			return;	// Quit if channel busy
		}''', 1)

old_sel = '''				// update for the next avail time，更新这个QP下一次可发送时间
				m_rdmaPktSent(lastQp, p, m_tInterframeGap);'''
need(c, old_sel, 1, 'dqt-sent')
c = c.replace(old_sel, '''				// Telemetry: capture m_nextAvail BEFORE the pacer advances it,
				// so the row carries old/new for the QP that actually sent.
				const uint64_t opp_old_na = lastQp->m_nextAvail.GetTimeStep();
				// update for the next avail time，更新这个QP下一次可发送时间
				m_rdmaPktSent(lastQp, p, m_tInterframeGap);
				if (SenderOppTrace::IsOpen() && SenderOppTrace::InWindow()){
					const int slot = SenderOppTrace::SlotOf(m_node->GetId(),
						m_ifIndex);
					if (slot >= 0){
						const uint64_t oid =
							SenderOppTrace::NextOpportunityId();
						EmitOppScan(slot, oid, qIndex, p ? p->GetUid() : 0,
							p ? p->GetSize() : 0, opp_old_na,
							lastQp->m_nextAvail.GetTimeStep(), 0);
					}
				}''', 1)

old_none = '''				if (m_nextSend.IsExpired() && t < Simulator::GetMaximumSimulationTime() && t > Simulator::Now()){
					m_nextSend = Simulator::Schedule(t - Simulator::Now(), &QbbNetDevice::DequeueAndTransmit, this);
				}
			}
			return;
		}else{   //switch, doesn't care about qcn, just send'''
need(c, old_none, 1, 'dqt-none')
c = c.replace(old_none, '''				const bool opp_armed_before = !m_nextSend.IsExpired();
				if (m_nextSend.IsExpired() && t < Simulator::GetMaximumSimulationTime() && t > Simulator::Now()){
					m_nextSend = Simulator::Schedule(t - Simulator::Now(), &QbbNetDevice::DequeueAndTransmit, this);
				}
				// Telemetry: no QP was selected.  WAKEUP_MISSING is reported
				// only when a finite min(m_nextAvail) existed in the future and
				// yet no wakeup is armed afterwards -- i.e. the port would sit
				// idle with work pending and nothing scheduled to revisit it.
				if (SenderOppTrace::IsOpen() && SenderOppTrace::InWindow()){
					const int slot = SenderOppTrace::SlotOf(m_node->GetId(),
						m_ifIndex);
					if (slot >= 0){
						const bool finite_future =
							t < Simulator::GetMaximumSimulationTime() &&
							t > Simulator::Now();
						const bool armed_after = !m_nextSend.IsExpired();
						const uint64_t wake = armed_after
							? m_nextSend.GetTs() : 0;
						const uint64_t oid =
							SenderOppTrace::NextOpportunityId();
						EmitOppScan(slot, oid, -1024, 0, 0, 0, 0, wake);
						if (finite_future && !armed_after)
							SenderOppTrace::Emit(slot, oid, "NO_SELECTION",
								"WAKEUP_MISSING", 0, 0, 0, 0, 0, 0, 0, 0, 0,
								0, 0, 0, 0, 0, wake, 0, -1024);
						(void)opp_armed_before;
					}
				}
			}
			return;
		}else{   //switch, doesn't care about qcn, just send''', 1)

# ---- helper that turns the scan record into rows ------------------------
if 'QbbNetDevice::EmitOppScan' not in c:
    a = '''	void
		QbbNetDevice::DequeueAndTransmit(void)'''
    need(c, a, 1, 'helper-anchor')
    c = c.replace(a, '''	// Telemetry helper: emit one row per QP examined in the scan that just ran,
	// refining the provisional "ELIGIBLE" label into SENT for the selected QP
	// and ELIGIBLE_NOT_SELECTED for the rest.  Read-only.
	void QbbNetDevice::EmitOppScan(int slot, uint64_t oppId, int selected,
			uint64_t sentUid, uint64_t sentBytes, uint64_t oldNa,
			uint64_t newNa, uint64_t wakeupNs)
	{
		const std::vector<RdmaEgressQueue::OppRec> &recs =
			RdmaEgressQueue::s_oppRec;
		for (uint32_t i = 0; i < recs.size(); ++i){
			const RdmaEgressQueue::OppRec &r = recs[i];
			const bool is_sel = ((int)r.idx == selected);
			const char *reason = r.reason;
			if (std::string(reason) == "ELIGIBLE")
				reason = is_sel ? "SENT" : "ELIGIBLE_NOT_SELECTED";
			const uint64_t interval = (is_sel && newNa > oldNa)
				? (newNa - oldNa) : 0;
			SenderOppTrace::Emit(slot, oppId,
				is_sel ? "SEND" : "SCAN", reason,
				r.idx, r.flowId, 0, r.batchId,
				is_sel ? sentUid : 0,
				r.bytesLeft ? 1 : 0, r.bytesLeft, r.rate, r.lastTx,
				is_sel ? sentBytes : 0, interval,
				is_sel ? oldNa : r.nextAvail,
				r.nextAvail, is_sel ? newNa : r.nextAvail,
				wakeupNs, 0, selected);
		}
	}

''' + a, 1)

# ---- header: declare OppRec + the helper -------------------------------
if 'struct OppRec' not in h:
    a = '	int GetNextQindex(bool paused[]);'
    need(h, a, 1, 'oppRec-anchor')
    h = h.replace(a, a + '''
	// Telemetry only: per-QP outcome of the most recent GetNextQindex scan.
	// Static because the scan and the emit happen in different objects; cleared
	// at the start of every scan.
	struct OppRec {
		uint32_t idx;
		uint64_t nextAvail;
		uint64_t bytesLeft;
		uint64_t rate;
		uint64_t lastTx;
		uint32_t flowId;
		uint32_t batchId;
		const char *reason;
	};
	static std::vector<OppRec> s_oppRec;
	static int s_oppSelected;''', 1)
    a2 = '  virtual void DequeueAndTransmit(void);'
    need(h, a2, 1, 'helper-decl-anchor')
    h = h.replace(a2, a2 + '''
	// Telemetry only.
	void EmitOppScan(int slot, uint64_t oppId, int selected, uint64_t sentUid,
		uint64_t sentBytes, uint64_t oldNa, uint64_t newNa,
		uint64_t wakeupNs);''', 1)

# ======================================================================= third
s = io.open(T, encoding='utf-8', errors='surrogateescape').read()
if 'SENDER_OPP_TRACE_FILE' not in s:
    a = '\t\t\telse if(key.compare("CAUSAL_QUEUE_TRACE_FILE")==0){'
    need(s, a, 1, 'third-cfg-anchor')
    s = s.replace(a, '''			else if(key.compare("SENDER_OPP_TRACE_FILE")==0){
				conf>>sender_opp_trace_file;
				std::cout << "SENDER_OPP_TRACE_FILE\\t\\t"
					<< sender_opp_trace_file << "\\n";
			}
			else if(key.compare("SENDER_OPP_TRACE_NODES")==0){
				conf>>sender_opp_trace_nodes;
				std::cout << "SENDER_OPP_TRACE_NODES\\t\\t"
					<< sender_opp_trace_nodes << "\\n";
			}
''' + a, 1)
    a = 'string causal_queue_trace_file = "", causal_pacer_trace_file = "";'
    need(s, a, 1, 'third-var-anchor')
    s = s.replace(a, a + '\nstring sender_opp_trace_file = "", '
                       'sender_opp_trace_nodes = "";', 1)

    # attach: open once, then register every sender port named in the config
    a = '\t// --- causal telemetry attach (both default OFF) -----------------------'
    need(s, a, 1, 'third-attach-anchor')
    s = s.replace(a, '''	// --- send-opportunity telemetry attach (default OFF) ------------------
	// Registers sender ports only.  Identical for CBAP and DCQCN: the emit
	// sites live in QbbNetDevice, shared by both.
	if (!sender_opp_trace_file.empty()){
		if (!ns3::SenderOppTrace::Open(sender_opp_trace_file,
				causal_trace_start_ns, causal_trace_end_ns, algorithm)){
			std::cout << "INVALID_SENDER_OPP_ATTACH cannot open trace\\n";
			return 2;
		}
		if (sender_opp_trace_nodes.empty()){
			std::cout << "INVALID_SENDER_OPP_ATTACH no nodes configured\\n";
			return 2;
		}
		uint32_t so_expected = 0, so_attached = 0;
		std::stringstream so_ss(sender_opp_trace_nodes);
		std::string so_tok;
		while (std::getline(so_ss, so_tok, ',')){
			if (so_tok.empty())
				continue;
			so_expected++;
			size_t cpos = so_tok.find(':');
			if (cpos == std::string::npos){
				std::cout << "INVALID_SENDER_OPP_ATTACH bad token "
					<< so_tok << "\\n";
				return 2;
			}
			uint32_t so_node = (uint32_t)atoi(so_tok.substr(0, cpos).c_str());
			uint32_t so_if = (uint32_t)atoi(so_tok.substr(cpos + 1).c_str());
			if (so_node >= n.GetN()){
				std::cout << "INVALID_SENDER_OPP_ATTACH node out of range "
					<< so_node << "\\n";
				return 2;
			}
			Ptr<QbbNetDevice> so_dev = DynamicCast<QbbNetDevice>(
				n.Get(so_node)->GetDevice(so_if));
			if (so_dev == 0){
				std::cout << "INVALID_SENDER_OPP_ATTACH not a qbb device "
					<< so_tok << "\\n";
				return 2;
			}
			int so_slot = ns3::SenderOppTrace::Register(so_attached, so_node,
				so_if);
			if (so_slot < 0){
				std::cout << "INVALID_SENDER_OPP_ATTACH duplicate "
					<< so_tok << "\\n";
				return 2;
			}
			so_attached++;
			std::cout << "SENDER_OPP_ATTACHED slot=" << so_slot
				<< " node=" << so_node << " if=" << so_if << "\\n";
		}
		if (so_attached != so_expected || so_attached == 0){
			std::cout << "INVALID_SENDER_OPP_ATTACH attached=" << so_attached
				<< " expected=" << so_expected << "\\n";
			return 2;
		}
		fflush(stdout);
	}
''' + a, 1)

    a = '\tns3::CausalQueueTrace::Close();'
    need(s, a, 1, 'third-close-anchor')
    s = s.replace(a, a + '\n\tns3::SenderOppTrace::Close();', 1)

# ---- single commit point: all anchors matched, now write ------------------
io.open(QBB, 'w', encoding='utf-8', errors='surrogateescape').write(c)
io.open(QBBH, 'w', encoding='utf-8', errors='surrogateescape').write(h)
io.open(T, 'w', encoding='utf-8', errors='surrogateescape').write(s)

print('sender-opp telemetry wired')
print('  qbb-net-device.cc  statics          : %d'
      % c.count('SenderOppTrace::s_file = 0'))
print('  qbb-net-device.cc  emit sites       : %d'
      % c.count('SenderOppTrace::Emit'))
print('  qbb-net-device.cc  IsOpen guards    : %d'
      % c.count('SenderOppTrace::IsOpen()'))
print('  qbb-net-device.h   OppRec declared  : %d' % h.count('struct OppRec'))
print('  third.cc  config keys               : %d'
      % (s.count('SENDER_OPP_TRACE_FILE') + s.count('SENDER_OPP_TRACE_NODES')))
print('  third.cc  fail-fast guards          : %d'
      % s.count('INVALID_SENDER_OPP_ATTACH'))
