/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
* Copyright (c) 2006 Georgia Tech Research Corporation, INRIA
*
* This program is free software; you can redistribute it and/or modify
* it under the terms of the GNU General Public License version 2 as
* published by the Free Software Foundation;
*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with this program; if not, write to the Free Software
* Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
*
* Author: Yuliang Li <yuliangli@g.harvard.com>
*/

#define __STDC_LIMIT_MACROS 1
#include <stdint.h>
#include <stdio.h>
#include "ns3/qbb-net-device.h"
#include "ns3/log.h"
#include "ns3/boolean.h"
#include "ns3/uinteger.h"
#include "ns3/double.h"
#include "ns3/data-rate.h"
#include "ns3/object-vector.h"
#include "ns3/pause-header.h"
#include "ns3/drop-tail-queue.h"
#include "ns3/assert.h"
#include "ns3/ipv4.h"
#include "ns3/ipv4-header.h"
#include "ns3/simulator.h"
#include "ns3/point-to-point-channel.h"
#include "ns3/qbb-channel.h"
#include "ns3/random-variable.h"
#include "ns3/flow-id-tag.h"
#include "ns3/qbb-header.h"
#include "ns3/error-model.h"
#include "ns3/cn-header.h"
#include "ns3/ppp-header.h"
#include "ns3/udp-header.h"
#include "ns3/seq-ts-header.h"
#include "ns3/pointer.h"
#include "ns3/custom-header.h"

#include <iostream>

NS_LOG_COMPONENT_DEFINE("QbbNetDevice");

namespace ns3 {
// Owned here: qbb-net-device.cc is inside libns3-point-to-point, which
// references these symbols.  Telemetry only.
FILE *SenderOppTrace::s_file = 0;
std::vector<SenderOppTrace::Key> SenderOppTrace::s_link;
std::string SenderOppTrace::s_algo = "";
uint64_t SenderOppTrace::s_lo = 0;
uint64_t SenderOppTrace::s_hi = 0;
uint64_t SenderOppTrace::s_rows = 0;
uint64_t SenderOppTrace::s_opp = 0;

	
	uint32_t RdmaEgressQueue::ack_q_idx = 3;
	// RdmaEgressQueue
	TypeId RdmaEgressQueue::GetTypeId (void)
	{
		static TypeId tid = TypeId ("ns3::RdmaEgressQueue")
			.SetParent<Object> ()
			.AddTraceSource ("RdmaEnqueue", "Enqueue a packet in the RdmaEgressQueue.",
					MakeTraceSourceAccessor (&RdmaEgressQueue::m_traceRdmaEnqueue))
			.AddTraceSource ("RdmaDequeue", "Dequeue a packet in the RdmaEgressQueue.",
					MakeTraceSourceAccessor (&RdmaEgressQueue::m_traceRdmaDequeue))
			;
		return tid;
	}

	RdmaEgressQueue::RdmaEgressQueue(){
		m_rrlast = 0;
		m_qlast = 0;
		m_ackQ = CreateObject<DropTailQueue>();
		m_ackQ->SetAttribute("MaxBytes", UintegerValue(0xffffffff)); // queue limit is on a higher level, not here
	}

	Ptr<Packet> RdmaEgressQueue::DequeueQindex(int qIndex){
		if (qIndex == -1){ // high prio
			Ptr<Packet> p = m_ackQ->Dequeue();
			m_qlast = -1;
			m_traceRdmaDequeue(p, 0);
			return p;
		}
		if (qIndex >= 0){ // qp
			Ptr<Packet> p = m_rdmaGetNxtPkt(m_qpGrp->Get(qIndex));//实际发包
			m_rrlast = qIndex;
			m_qlast = qIndex;
			m_traceRdmaDequeue(p, m_qpGrp->Get(qIndex)->m_pg);
			return p;
		}
		return 0;
	}
	// Telemetry: per-QP outcome of the most recent scan.  Filled read-only by
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
			return -1;

		// no pkt in highest priority queue, do rr for each qp
		int res = -1024;
		uint32_t fcount = m_qpGrp->GetN();
		uint32_t min_finish_id = 0xffffffff;//把初始值设置成最大值表示还没发现结束的QP队列
		for (qIndex = 1; qIndex <= fcount; qIndex++){
			uint32_t idx = (qIndex + m_rrlast) % fcount;
			Ptr<RdmaQueuePair> qp = m_qpGrp->Get(idx);
			if (trace_opp){
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
			}
		}

		// clear the finished qp
		if (min_finish_id < 0xffffffff){//如果min_finish_id被更新过，说明至少发现一个finished QP
			int nxt = min_finish_id;//这个nxt储存下一个应该防止未完成QP的位置，也就是从第一个QPfinished位置开始，把后面未完成的QP往前挪
			auto &qps = m_qpGrp->m_qps;//拿到QP数组的引用
			for (int i = min_finish_id + 1; i < fcount; i++) if (!qps[i]->IsFinished()){
				if (i == res) // update res to the idx after removing finished qp
					res = nxt;
				qps[nxt] = qps[i];
				nxt++;
			}
			qps.resize(nxt);
		}
		s_oppSelected = res;
		return res;
	}

	int RdmaEgressQueue::GetLastQueue(){
		return m_qlast;
	}

	uint32_t RdmaEgressQueue::GetNBytes(uint32_t qIndex){
		NS_ASSERT_MSG(qIndex < m_qpGrp->GetN(), "RdmaEgressQueue::GetNBytes: qIndex >= m_qpGrp->GetN()");
		return m_qpGrp->Get(qIndex)->GetBytesLeft();
	}

	uint32_t RdmaEgressQueue::GetFlowCount(void){
		return m_qpGrp->GetN();
	}

	Ptr<RdmaQueuePair> RdmaEgressQueue::GetQp(uint32_t i){
		return m_qpGrp->Get(i);
	}
 
	void RdmaEgressQueue::RecoverQueue(uint32_t i){
		NS_ASSERT_MSG(i < m_qpGrp->GetN(), "RdmaEgressQueue::RecoverQueue: qIndex >= m_qpGrp->GetN()");
		m_qpGrp->Get(i)->snd_nxt = m_qpGrp->Get(i)->snd_una;
	}

	void RdmaEgressQueue::EnqueueHighPrioQ(Ptr<Packet> p){
		m_traceRdmaEnqueue(p, 0);
		m_ackQ->Enqueue(p);
	}

	void RdmaEgressQueue::CleanHighPrio(TracedCallback<Ptr<const Packet>, uint32_t> dropCb){
		while (m_ackQ->GetNPackets() > 0){
			Ptr<Packet> p = m_ackQ->Dequeue();
			dropCb(p, 0);
		}
	}

	/******************
	 * QbbNetDevice
	 *****************/
	NS_OBJECT_ENSURE_REGISTERED(QbbNetDevice);

	TypeId
		QbbNetDevice::GetTypeId(void)
	{
		static TypeId tid = TypeId("ns3::QbbNetDevice")
			.SetParent<PointToPointNetDevice>()
			.AddConstructor<QbbNetDevice>()
			.AddAttribute("QbbEnabled",
				"Enable the generation of PAUSE packet.",
				BooleanValue(true),
				MakeBooleanAccessor(&QbbNetDevice::m_qbbEnabled),
				MakeBooleanChecker())
			.AddAttribute("QcnEnabled",
				"Enable the generation of PAUSE packet.",
				BooleanValue(false),
				MakeBooleanAccessor(&QbbNetDevice::m_qcnEnabled),
				MakeBooleanChecker())
			.AddAttribute("DynamicThreshold",
				"Enable dynamic threshold.",
				BooleanValue(false),
				MakeBooleanAccessor(&QbbNetDevice::m_dynamicth),
				MakeBooleanChecker())
			.AddAttribute("PauseTime",
				"Number of microseconds to pause upon congestion",
				UintegerValue(5),
				MakeUintegerAccessor(&QbbNetDevice::m_pausetime),
				MakeUintegerChecker<uint32_t>())
			.AddAttribute ("TxBeQueue", 
					"A queue to use as the transmit queue in the device.",
					PointerValue (),
					MakePointerAccessor (&QbbNetDevice::m_queue),
					MakePointerChecker<Queue> ())
			.AddAttribute ("RdmaEgressQueue", 
					"A queue to use as the transmit queue in the device.",
					PointerValue (),
					MakePointerAccessor (&QbbNetDevice::m_rdmaEQ),
					MakePointerChecker<Object> ())
			.AddTraceSource ("QbbEnqueue", "Enqueue a packet in the QbbNetDevice.",
					MakeTraceSourceAccessor (&QbbNetDevice::m_traceEnqueue))
			.AddTraceSource ("QbbDequeue", "Dequeue a packet in the QbbNetDevice.",
					MakeTraceSourceAccessor (&QbbNetDevice::m_traceDequeue))
			.AddTraceSource ("QbbDrop", "Drop a packet in the QbbNetDevice.",
					MakeTraceSourceAccessor (&QbbNetDevice::m_traceDrop))
			.AddTraceSource ("RdmaQpDequeue", "A qp dequeue a packet.",
					MakeTraceSourceAccessor (&QbbNetDevice::m_traceQpDequeue))
			.AddTraceSource ("QbbPfc", "get a PFC packet. 0: resume, 1: pause",
					MakeTraceSourceAccessor (&QbbNetDevice::m_tracePfc))
			.AddTraceSource ("PfcSemantic",
					"Event-level PFC receive/state trace: priority, event, queue, pause quanta.",
					MakeTraceSourceAccessor (&QbbNetDevice::m_tracePfcSemantic))
			;

		return tid;
	}

	QbbNetDevice::QbbNetDevice()
	{
		NS_LOG_FUNCTION(this);
		m_ecn_source = new std::vector<ECNAccount>;
		for (uint32_t i = 0; i < qCnt; i++){
			m_paused[i] = false;
		}

		m_rdmaEQ = CreateObject<RdmaEgressQueue>();
	}

	QbbNetDevice::~QbbNetDevice()
	{
		NS_LOG_FUNCTION(this);
	}

	bool QbbNetDevice::IsPaused(uint32_t qIndex) const
	{
		return qIndex < qCnt && m_paused[qIndex];
	}

	void
		QbbNetDevice::DoDispose()
	{
		NS_LOG_FUNCTION(this);

		PointToPointNetDevice::DoDispose();
	}

	void
		QbbNetDevice::TransmitComplete(void)
	{
		NS_LOG_FUNCTION(this);
		NS_ASSERT_MSG(m_txMachineState == BUSY, "Must be BUSY if transmitting");
		m_txMachineState = READY;
		NS_ASSERT_MSG(m_currentPkt != 0, "QbbNetDevice::TransmitComplete(): m_currentPkt zero");
		m_phyTxEndTrace(m_currentPkt);
		m_currentPkt = 0;
		DequeueAndTransmit();
	}

	// Telemetry helper: emit one row per QP examined in the scan that just ran,
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

	void
		QbbNetDevice::DequeueAndTransmit(void)
	{
		NS_LOG_FUNCTION(this);
		if (!m_linkUp) return; // if link is down, return
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
		}
		Ptr<Packet> p;
		if (m_node->GetNodeType() == 0){
			int qIndex = m_rdmaEQ->GetNextQindex(m_paused);
			if (qIndex != -1024){
				if (qIndex == -1){ // high prio
					p = m_rdmaEQ->DequeueQindex(qIndex);
					m_traceDequeue(p, 0);
					TransmitStart(p);
					return;
				}
				// a qp dequeue a packet
				Ptr<RdmaQueuePair> lastQp = m_rdmaEQ->GetQp(qIndex);//更新这个last QP，这个last QP指的是上一次发包的QP
				p = m_rdmaEQ->DequeueQindex(qIndex);

				// transmit
				m_traceQpDequeue(p, lastQp);
				TransmitStart(p);

				// Telemetry: capture m_nextAvail BEFORE the pacer advances it,
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
				}
			}else { // no packet to send
				NS_LOG_INFO("PAUSE prohibits send at node " << m_node->GetId());
				Time t = Simulator::GetMaximumSimulationTime();
				for (uint32_t i = 0; i < m_rdmaEQ->GetFlowCount(); i++){
					Ptr<RdmaQueuePair> qp = m_rdmaEQ->GetQp(i);
					if (qp->GetBytesLeft() == 0 || qp->cbap.zeroGrantPaused)
						continue;
					t = Min(qp->m_nextAvail, t);
				}
				const bool opp_armed_before = !m_nextSend.IsExpired();
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
		}else{   //switch, doesn't care about qcn, just send
			p = m_queue->DequeueRR(m_paused);		//this is round-robin
			if (p != 0){
				m_snifferTrace(p);
				m_promiscSnifferTrace(p);
				Ipv4Header h;
				Ptr<Packet> packet = p->Copy();
				uint16_t protocol = 0;
				ProcessHeader(packet, protocol);
				packet->RemoveHeader(h);
				FlowIdTag t;
				uint32_t qIndex = m_queue->GetLastQueue();
				if (qIndex == 0){//this is a pause or cnp, send it immediately!
					m_node->SwitchNotifyDequeue(m_ifIndex, qIndex, p);
					p->RemovePacketTag(t);
				}else{
					m_node->SwitchNotifyDequeue(m_ifIndex, qIndex, p);
					p->RemovePacketTag(t);
				}
				m_traceDequeue(p, qIndex);
				TransmitStart(p);
				return;
			}else{ //No queue can deliver any packet
				NS_LOG_INFO("PAUSE prohibits send at node " << m_node->GetId());
				if (m_node->GetNodeType() == 0 && m_qcnEnabled){ //nothing to send, possibly due to qcn flow control, if so reschedule sending
					Time t = Simulator::GetMaximumSimulationTime();
					for (uint32_t i = 0; i < m_rdmaEQ->GetFlowCount(); i++){
						Ptr<RdmaQueuePair> qp = m_rdmaEQ->GetQp(i);
						if (qp->GetBytesLeft() == 0 ||
								qp->cbap.zeroGrantPaused)
							continue;
						t = Min(qp->m_nextAvail, t);
					}
					if (m_nextSend.IsExpired() && t < Simulator::GetMaximumSimulationTime() && t > Simulator::Now()){
						m_nextSend = Simulator::Schedule(t - Simulator::Now(), &QbbNetDevice::DequeueAndTransmit, this);
					}
				}
			}
		}
		return;
	}

	void
		QbbNetDevice::Resume(unsigned qIndex)
	{
		NS_LOG_FUNCTION(this << qIndex);
		NS_ASSERT_MSG(m_paused[qIndex], "Must be PAUSEd");
		m_paused[qIndex] = false;
		NS_LOG_INFO("Node " << m_node->GetId() << " dev " << m_ifIndex << " queue " << qIndex <<
			" resumed at " << Simulator::Now().GetSeconds());
		DequeueAndTransmit();
	}

	void
		QbbNetDevice::Receive(Ptr<Packet> packet)
	{
		NS_LOG_FUNCTION(this << packet);
		if (!m_linkUp){
			m_traceDrop(packet, 0);
			return;
		}

		if (m_receiveErrorModel && m_receiveErrorModel->IsCorrupt(packet))
		{
			// 
			// If we have an error model and it indicates that it is time to lose a
			// corrupted packet, don't forward this packet up, let it go.
			//
			m_phyRxDropTrace(packet);
			return;
		}

		m_macRxTrace(packet);
		CustomHeader ch(CustomHeader::L2_Header | CustomHeader::L3_Header | CustomHeader::L4_Header);
		ch.getInt = 1; // parse INT header
		packet->PeekHeader(ch);
		if (ch.l3Prot == 0xFE){ // PFC
			if (!m_qbbEnabled) return;
			unsigned qIndex = ch.pfc.qIndex;
			if (ch.pfc.time > 0){
				m_tracePfcSemantic(qIndex, 1, ch.pfc.qlen, ch.pfc.time);
				m_tracePfc(qIndex, 1);
				m_paused[qIndex] = true;
				m_tracePfcSemantic(qIndex, 2, ch.pfc.qlen, ch.pfc.time);
			}else{
				m_tracePfcSemantic(qIndex, 4, ch.pfc.qlen, ch.pfc.time); 
				m_tracePfc(qIndex, 0);
				Resume(qIndex);
				m_tracePfcSemantic(qIndex, 5, ch.pfc.qlen, ch.pfc.time);
			}
		}else { // non-PFC packets (data, ACK, NACK, CNP...)
			if (m_node->GetNodeType() > 0){ // switch
				packet->AddPacketTag(FlowIdTag(m_ifIndex));//FlowIdTag中保存着这个包从交换机哪个入口端口进入
				m_node->SwitchReceiveFromDevice(this, packet, ch);
			}else { // NIC
				// send to RdmaHw
				int ret = m_rdmaReceiveCb(packet, ch);
				// TODO we may based on the ret do something
			}
		}
		return;
	}

	bool QbbNetDevice::Send(Ptr<Packet> packet, const Address &dest, uint16_t protocolNumber)
	{
		NS_ASSERT_MSG(false, "QbbNetDevice::Send not implemented yet\n");
		return false;
	}

	bool QbbNetDevice::SwitchSend (uint32_t qIndex, Ptr<Packet> packet, CustomHeader &ch){
		m_macTxTrace(packet);
		m_traceEnqueue(packet, qIndex);
		m_queue->Enqueue(packet, qIndex);
		DequeueAndTransmit();
		return true;
	}

	void QbbNetDevice::SendPfc(uint32_t qIndex, uint32_t type){
		Ptr<Packet> p = Create<Packet>(0);
		PauseHeader pauseh((type == 0 ? m_pausetime : 0), m_queue->GetNBytes(qIndex), qIndex);
		p->AddHeader(pauseh);
		Ipv4Header ipv4h;  // Prepare IPv4 header
		ipv4h.SetProtocol(0xFE);
		ipv4h.SetSource(m_node->GetObject<Ipv4>()->GetAddress(m_ifIndex, 0).GetLocal());
		ipv4h.SetDestination(Ipv4Address("255.255.255.255"));
		ipv4h.SetPayloadSize(p->GetSize());
		ipv4h.SetTtl(1);
		ipv4h.SetIdentification(UniformVariable(0, 65536).GetValue());
		p->AddHeader(ipv4h);
		AddHeader(p, 0x800);
		CustomHeader ch(CustomHeader::L2_Header | CustomHeader::L3_Header | CustomHeader::L4_Header);
		p->PeekHeader(ch);
		SwitchSend(0, p, ch);
	}

	bool
		QbbNetDevice::Attach(Ptr<QbbChannel> ch)
	{
		NS_LOG_FUNCTION(this << &ch);
		m_channel = ch;
		m_channel->Attach(this);
		NotifyLinkUp();
		return true;
	}

	bool
		QbbNetDevice::TransmitStart(Ptr<Packet> p)
	{
		NS_LOG_FUNCTION(this << p);
		NS_LOG_LOGIC("UID is " << p->GetUid() << ")");
		//
		// This function is called to start the process of transmitting a packet.
		// We need to tell the channel that we've started wiggling the wire and
		// schedule an event that will be executed when the transmission is complete.
		//
		NS_ASSERT_MSG(m_txMachineState == READY, "Must be READY to transmit");
		m_txMachineState = BUSY;
		m_currentPkt = p;
		m_phyTxBeginTrace(m_currentPkt);
		Time txTime = Seconds(m_bps.CalculateTxTime(p->GetSize()));
		Time txCompleteTime = txTime + m_tInterframeGap;
		NS_LOG_LOGIC("Schedule TransmitCompleteEvent in " << txCompleteTime.GetSeconds() << "sec");
		Simulator::Schedule(txCompleteTime, &QbbNetDevice::TransmitComplete, this);

		bool result = m_channel->TransmitStart(p, this, txTime);
		if (result == false)
		{
			m_phyTxDropTrace(p);
		}
		return result;
	}

	Ptr<Channel>
		QbbNetDevice::GetChannel(void) const
	{
		return m_channel;
	}

   bool QbbNetDevice::IsQbb(void) const{
	   return true;
   }

   void QbbNetDevice::NewQp(Ptr<RdmaQueuePair> qp){
	   qp->m_nextAvail = Simulator::Now();
	   DequeueAndTransmit();
   }
   void QbbNetDevice::ReassignedQp(Ptr<RdmaQueuePair> qp){
	   DequeueAndTransmit();
   }
   void QbbNetDevice::TriggerTransmit(void){
	   DequeueAndTransmit();
   }

	void QbbNetDevice::SetQueue(Ptr<BEgressQueue> q){
		NS_LOG_FUNCTION(this << q);
		m_queue = q;
	}

	Ptr<BEgressQueue> QbbNetDevice::GetQueue(){
		return m_queue;
	}

	Ptr<RdmaEgressQueue> QbbNetDevice::GetRdmaQueue(){
		return m_rdmaEQ;
	}

	void QbbNetDevice::RdmaEnqueueHighPrioQ(Ptr<Packet> p){
		m_traceEnqueue(p, 0);
		m_rdmaEQ->EnqueueHighPrioQ(p);
	}

	void QbbNetDevice::TakeDown(){
		// TODO: delete packets in the queue, set link down
		if (m_node->GetNodeType() == 0){
			// clean the high prio queue
			m_rdmaEQ->CleanHighPrio(m_traceDrop);
			// notify driver/RdmaHw that this link is down
			m_rdmaLinkDownCb(this);
		}else { // switch
			// clean the queue
			for (uint32_t i = 0; i < qCnt; i++)
				m_paused[i] = false;
			while (1){
				Ptr<Packet> p = m_queue->DequeueRR(m_paused);
				if (p == 0)
					 break;
				m_traceDrop(p, m_queue->GetLastQueue());
			}
			// TODO: Notify switch that this link is down
		}
		m_linkUp = false;
	}

	void QbbNetDevice::UpdateNextAvail(Time t){
		if (!m_nextSend.IsExpired() && t < m_nextSend.GetTs()){
			Simulator::Cancel(m_nextSend);
			Time delta = t < Simulator::Now() ? Time(0) : t - Simulator::Now();
			m_nextSend = Simulator::Schedule(delta, &QbbNetDevice::DequeueAndTransmit, this);
		}
	}

	void QbbNetDevice::InvalidateAndRescheduleRdma(void){
		if (!m_nextSend.IsExpired())
			Simulator::Cancel(m_nextSend);
		// DequeueAndTransmit scans every QP.  If the link is busy its normal
		// TransmitComplete callback performs the scan; otherwise this call
		// schedules the minimum currently eligible m_nextAvail.
		DequeueAndTransmit();
	}
} // namespace ns3
