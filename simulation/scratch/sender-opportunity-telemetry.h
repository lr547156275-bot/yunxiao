// Send-opportunity telemetry: one row per SEND OPPORTUNITY at the sender NIC,
// for BOTH CBAP and DCQCN, under an identical schema and identical emit sites.
//
// DEFAULT OFF.  Read-only.  No Simulator::Schedule / Cancel / Remove; only
// Simulator::Now().  With no output path configured, Open() returns false and
// nothing is emitted, so the run must stay bit-identical.
//
// WHY THIS EXISTS
// The previous round localized the layer but not the cause:
//   ROOT_CAUSE_LAYER_LOCALIZED_SENDER_UNDERFEED_EXACT_CAUSE_UNKNOWN
// 98.74 % of CBAP's excess bottleneck idle time occurs with an EMPTY bottleneck
// queue, and no rate command occurs in the 58.19 ms where 1,054 of those gaps
// live.  So the next packet was late leaving the SENDER.  The prior pacer trace
// only fired at rate changes, which is why the cause stayed unknown.  This
// tracer fires at every send opportunity instead.
//
// EMIT SITES (all inside QbbNetDevice::DequeueAndTransmit / RdmaEgressQueue::
// GetNextQindex, host path only):
//   1. entry, when the NIC is BUSY                    -> NIC_BUSY
//   2. per-QP, inside the round-robin scan            -> the blocking reason
//   3. the QP actually dequeued                       -> SENT
//   4. the no-candidate branch, with the computed wakeup -> WAKEUP_MISSING or
//      NEXT_AVAIL_FUTURE depending on whether a wakeup was armed
//
// REASON ENUM -- MUTUALLY EXCLUSIVE, evaluated in a fixed order so exactly one
// applies to each (opportunity, QP) pair:
//   SENT                   this QP was selected and a packet was dequeued
//   NIC_BUSY               m_txMachineState == BUSY at opportunity entry
//   FLOW_FINISHED          qp->IsFinished()
//   HANDOFF_PENDING        qp->cbap.zeroGrantPaused (zero-grant / handoff hold)
//   NO_PACKET              qp->GetBytesLeft() == 0, or window-bound (no data
//                          may be released) -- nothing to hand to the wire
//   NEXT_AVAIL_FUTURE      eligible with data, but m_nextAvail > now
//   ELIGIBLE_NOT_SELECTED  eligible AND m_nextAvail <= now, but the RR scan
//                          selected a different QP this opportunity
//   WAKEUP_MISSING         no QP was selected, and no wakeup event was armed
//                          even though a finite min(m_nextAvail) existed
// UNKNOWN is deliberately NOT in the enum: the classifier must reach 0 unknown,
// and if it cannot, that is a missing-field report, not a bucket.
#ifndef SENDER_OPPORTUNITY_TELEMETRY_H
#define SENDER_OPPORTUNITY_TELEMETRY_H

#include <cstdio>
#include <string>
#include <vector>
#include <ns3/simulator.h>

namespace ns3 {

class SenderOppTrace {
public:
	static bool Open(const std::string &path, uint64_t winStartNs,
			uint64_t winEndNs, const std::string &algo)
	{
		if (path.empty())
			return false;
		s_file = fopen(path.c_str(), "w");
		if (!s_file)
			return false;
		s_lo = winStartNs;
		s_hi = winEndNs;
		s_algo = algo;
		s_rows = 0;
		s_opp = 0;
		fprintf(s_file,
			"time_ns,algo,link_id,node_id,if_index,opportunity_id,"
			"qp_id,flow_id,generation,batch_id,packet_uid,event,"
			"pending_packets,pending_bytes,rate_bps,last_tx_ns,"
			"packet_bytes,interval_ns,old_next_avail_ns,"
			"candidate_next_avail_ns,new_next_avail_ns,"
			"scheduled_wakeup_ns,nic_busy_until_ns,selected_qp,reason\n");
		return true;
	}
	static void Close()
	{
		if (s_file) { fclose(s_file); s_file = 0; }
	}
	static bool IsOpen() { return s_file != 0; }
	static uint64_t Rows() { return s_rows; }

	// Registered per monitored sender port so identity comes from registration
	// rather than from a guess at trace time.
	static int Register(uint32_t linkId, uint32_t nodeId, uint32_t ifIndex)
	{
		for (uint32_t i = 0; i < s_link.size(); ++i)
			if (s_link[i].n == nodeId && s_link[i].i == ifIndex)
				return -1;                       // duplicate attach
		Key k; k.l = linkId; k.n = nodeId; k.i = ifIndex;
		s_link.push_back(k);
		return (int)s_link.size() - 1;
	}
	static uint32_t LinkCount() { return (uint32_t)s_link.size(); }

	// Returns -1 when this (node, if) is not monitored, so callers can skip all
	// per-QP work on unmonitored ports and keep the hot path cheap.
	static int SlotOf(uint32_t nodeId, uint32_t ifIndex)
	{
		if (!s_file)
			return -1;
		for (uint32_t i = 0; i < s_link.size(); ++i)
			if (s_link[i].n == nodeId && s_link[i].i == ifIndex)
				return (int)i;
		return -1;
	}

	// One opportunity == one DequeueAndTransmit invocation on a monitored port.
	// The id ties together every row emitted by that invocation, so the reader
	// can reconstruct "who else was eligible when this QP was skipped".
	static uint64_t NextOpportunityId() { return ++s_opp; }
	static bool InWindow()
	{
		if (!s_file)
			return false;
		const uint64_t now = Simulator::Now().GetTimeStep();
		return !(s_hi > 0 && (now < s_lo || now > s_hi));
	}

	static void Emit(int slot, uint64_t oppId, const char *event,
			const char *reason, uint64_t qpId, uint64_t flowId,
			uint64_t generation, uint64_t batchId, uint64_t packetUid,
			uint64_t pendingPkts, uint64_t pendingBytes, uint64_t rateBps,
			uint64_t lastTxNs, uint64_t packetBytes, uint64_t intervalNs,
			uint64_t oldNextAvail, uint64_t candNextAvail,
			uint64_t newNextAvail, uint64_t wakeupNs,
			uint64_t nicBusyUntilNs, int64_t selectedQp)
	{
		if (!s_file || slot < 0 || (uint32_t)slot >= s_link.size())
			return;
		const uint64_t now = Simulator::Now().GetTimeStep();
		if (s_hi > 0 && (now < s_lo || now > s_hi))
			return;
		const Key &k = s_link[slot];
		fprintf(s_file,
			"%lu,%s,%u,%u,%u,%lu,%lu,%lu,%lu,%lu,%lu,%s,"
			"%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%ld,%s\n",
			(unsigned long)now, s_algo.c_str(), k.l, k.n, k.i,
			(unsigned long)oppId, (unsigned long)qpId,
			(unsigned long)flowId, (unsigned long)generation,
			(unsigned long)batchId, (unsigned long)packetUid, event,
			(unsigned long)pendingPkts, (unsigned long)pendingBytes,
			(unsigned long)rateBps, (unsigned long)lastTxNs,
			(unsigned long)packetBytes, (unsigned long)intervalNs,
			(unsigned long)oldNextAvail, (unsigned long)candNextAvail,
			(unsigned long)newNextAvail, (unsigned long)wakeupNs,
			(unsigned long)nicBusyUntilNs, (long)selectedQp, reason);
		s_rows++;
	}

private:
	struct Key { uint32_t l, n, i; };
	static FILE *s_file;
	static std::vector<Key> s_link;
	static std::string s_algo;
	static uint64_t s_lo, s_hi, s_rows, s_opp;
};

} // namespace ns3

#endif // SENDER_OPPORTUNITY_TELEMETRY_H
