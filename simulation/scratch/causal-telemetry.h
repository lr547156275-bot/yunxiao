// Pure-observation event-level causal telemetry.  Two independent tracers,
// both DEFAULT OFF, both read-only.
//
// WHY: the previous gap classification used a 10 us port_summary sample to judge
// nanosecond-scale gaps, so "queue non-empty while port idle" (91.76 % of CBAP
// gap time) could not be distinguished from a stale reading.  These tracers
// record the queue depth AT THE EVENT INSTANT, and the pacer state at every
// rate-change decision point.
//
// BYPASS GUARANTEES, by construction:
//   * No Simulator::Schedule / Cancel / Remove anywhere in this file.  Only
//     Simulator::Now(), read-only.
//   * No packet, device, queue, QP or controller state is mutated.  Callbacks
//     take const pointers where the trace source allows.
//   * Event ORDER is not altered: the tracers are attached to existing trace
//     sources that already fire; attaching a callback cannot reorder events.
//   * With no output path configured, Open() returns false, nothing is
//     registered, no file is created, and the run must be bit-identical.
//
// QUEUE SEMANTICS, established from source (broadcom-egress-queue.cc):
//   BeqEnqueue fires AFTER  m_bytesInQueueTotal += p->GetSize()
//   BeqDequeue fires BEFORE m_bytesInQueueTotal -= p->GetSize()
// So at callback time GetNBytesTotal() is:
//   enqueue -> already includes this packet   (q_after)
//   dequeue -> still  includes this packet    (q_before)
// Both are recorded explicitly so no reader has to guess.
//
// The queue counter does NOT include a packet currently being serialized: it is
// removed from the queue at dequeue, then handed to TransmitStart.  That is why
// device_busy is recorded alongside.
#ifndef CAUSAL_TELEMETRY_H
#define CAUSAL_TELEMETRY_H

#include <cstdio>
#include <string>
#include <vector>
#include <ns3/packet.h>
#include <ns3/ptr.h>
#include <ns3/simulator.h>

namespace ns3 {

// ---------------------------------------------------------------- queue -----
class CausalQueueTrace {
public:
	static bool Open(const std::string &path, uint64_t winStartNs,
			uint64_t winEndNs)
	{
		if (path.empty())
			return false;
		s_file = fopen(path.c_str(), "w");
		if (!s_file)
			return false;
		s_lo = winStartNs;
		s_hi = winEndNs;
		fprintf(s_file,
			"time_ns,event,link_id,node_id,if_index,queue_index,"
			"packet_uid,packet_bytes,"
			"q_bytes_before,q_bytes_after,q_packets_before,q_packets_after,"
			"device_busy,service_packet_uid\n");
		return true;
	}
	static void Close()
	{
		if (s_file) { fclose(s_file); s_file = 0; }
	}
	static bool IsOpen() { return s_file != 0; }
	static uint64_t Rows() { return s_rows; }

	// Registered per monitored link so identity comes from registration.
	static int Register(uint32_t linkId, uint32_t nodeId, uint32_t ifIndex)
	{
		for (uint32_t i = 0; i < s_link.size(); ++i)
			if (s_link[i].l == linkId && s_link[i].n == nodeId &&
					s_link[i].i == ifIndex)
				return -1;                      // duplicate attach
		Key k; k.l = linkId; k.n = nodeId; k.i = ifIndex;
		s_link.push_back(k);
		return (int)s_link.size() - 1;
	}
	static uint32_t LinkCount() { return (uint32_t)s_link.size(); }

	// BeqEnqueue: counter ALREADY updated -> value is q_after.
	static void OnEnqueue(uint32_t slot, uint64_t qBytesNow,
			uint64_t qPktsNow, Ptr<const Packet> p, uint32_t qIndex,
			bool busy, uint64_t servingUid)
	{
		if (!p) return;
		const uint64_t sz = p->GetSize();
		Emit(slot, "ENQUEUE", qIndex, p->GetUid(), sz,
			qBytesNow >= sz ? qBytesNow - sz : 0, qBytesNow,
			qPktsNow >= 1 ? qPktsNow - 1 : 0, qPktsNow, busy, servingUid);
	}
	// BeqDequeue: counter NOT yet updated -> value is q_before.
	static void OnDequeue(uint32_t slot, uint64_t qBytesNow,
			uint64_t qPktsNow, Ptr<const Packet> p, uint32_t qIndex,
			bool busy, uint64_t servingUid)
	{
		if (!p) return;
		const uint64_t sz = p->GetSize();
		Emit(slot, "DEQUEUE", qIndex, p->GetUid(), sz,
			qBytesNow, qBytesNow >= sz ? qBytesNow - sz : 0,
			qPktsNow, qPktsNow >= 1 ? qPktsNow - 1 : 0, busy, servingUid);
	}
	static void OnTxBegin(uint32_t slot, uint64_t qBytesNow,
			uint64_t qPktsNow, Ptr<const Packet> p)
	{
		if (!p) return;
		Emit(slot, "TX_BEGIN", 0, p->GetUid(), p->GetSize(),
			qBytesNow, qBytesNow, qPktsNow, qPktsNow, true, p->GetUid());
	}
	static void OnTxEnd(uint32_t slot, uint64_t qBytesNow,
			uint64_t qPktsNow, Ptr<const Packet> p)
	{
		if (!p) return;
		Emit(slot, "TX_END", 0, p->GetUid(), p->GetSize(),
			qBytesNow, qBytesNow, qPktsNow, qPktsNow, false, p->GetUid());
	}

private:
	struct Key { uint32_t l, n, i; };
	static void Emit(uint32_t slot, const char *ev, uint32_t qIndex,
			uint64_t uid, uint64_t bytes, uint64_t qb, uint64_t qa,
			uint64_t pb, uint64_t pa, bool busy, uint64_t serving)
	{
		if (!s_file || slot >= s_link.size()) return;
		const uint64_t now = Simulator::Now().GetTimeStep();
		if (s_hi > 0 && (now < s_lo || now > s_hi)) return;
		const Key &k = s_link[slot];
		fprintf(s_file,
			"%lu,%s,%u,%u,%u,%u,%lu,%lu,%lu,%lu,%lu,%lu,%u,%lu\n",
			(unsigned long)now, ev, k.l, k.n, k.i, qIndex,
			(unsigned long)uid, (unsigned long)bytes,
			(unsigned long)qb, (unsigned long)qa,
			(unsigned long)pb, (unsigned long)pa,
			busy ? 1u : 0u, (unsigned long)serving);
		s_rows++;
	}
	static FILE *s_file;
	static std::vector<Key> s_link;
	static uint64_t s_lo, s_hi, s_rows;
};

// ------------------------------------------------------------------ pacer ---
class CausalPacerTrace {
public:
	static bool Open(const std::string &path, uint64_t winStartNs,
			uint64_t winEndNs)
	{
		if (path.empty())
			return false;
		s_file = fopen(path.c_str(), "w");
		if (!s_file)
			return false;
		s_lo = winStartNs;
		s_hi = winEndNs;
		fprintf(s_file,
			"time_ns,flow_id,qp_id,generation,reason,"
			"old_rate_bps,new_rate_bps,last_tx_time_ns,"
			"old_next_avail_ns,candidate_next_avail_ns,new_next_avail_ns,"
			"old_send_event_ns,new_send_event_ns,event_action,"
			"sender_pending_packets\n");
		return true;
	}
	static void Close()
	{
		if (s_file) { fclose(s_file); s_file = 0; }
	}
	static bool IsOpen() { return s_file != 0; }
	static uint64_t Rows() { return s_rows; }

	static void Emit(uint64_t flowId, uint64_t qpId, uint64_t generation,
			const char *reason, uint64_t oldRate, uint64_t newRate,
			uint64_t lastTxNs, uint64_t oldNextAvail,
			uint64_t candNextAvail, uint64_t newNextAvail,
			uint64_t oldEventNs, uint64_t newEventNs,
			const char *action, uint64_t pendingPkts)
	{
		if (!s_file) return;
		const uint64_t now = Simulator::Now().GetTimeStep();
		if (s_hi > 0 && (now < s_lo || now > s_hi)) return;
		fprintf(s_file,
			"%lu,%lu,%lu,%lu,%s,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%s,%lu\n",
			(unsigned long)now, (unsigned long)flowId,
			(unsigned long)qpId, (unsigned long)generation, reason,
			(unsigned long)oldRate, (unsigned long)newRate,
			(unsigned long)lastTxNs, (unsigned long)oldNextAvail,
			(unsigned long)candNextAvail, (unsigned long)newNextAvail,
			(unsigned long)oldEventNs, (unsigned long)newEventNs,
			action, (unsigned long)pendingPkts);
		s_rows++;
	}

private:
	static FILE *s_file;
	static uint64_t s_lo, s_hi, s_rows;
};

} // namespace ns3

#endif // CAUSAL_TELEMETRY_H
