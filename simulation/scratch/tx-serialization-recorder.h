// Pure-observation per-packet TX serialization recorder.
//
// Acceptance INFRASTRUCTURE only.  It exists so R-1a/R-1b/R-1c can be evaluated
// from real per-packet events instead of from 5 us aggregate windows, whose
// whole-packet completion counting produced the INVALID_GATE_PACKET_COMPLETION_
// QUANTIZATION artefact (6288 B / 5 us = 10.0608 Gbps, because a 5 us window
// holds 5.9637 packets of 1048 B).
//
// Bypass guarantees, by construction:
//   * It only ever READS from the PhyTxBegin / PhyTxEnd trace sources that
//     QbbNetDevice already fires (qbb-net-device.cc:464 and :261).
//   * It schedules, cancels and delays NOTHING.  No Simulator:: call appears
//     anywhere in this file.
//   * It mutates no packet, no device, no queue and no controller state.
//   * When the output file is not configured, Configure() returns false, the
//     callbacks are never connected, no file is created, and the run must be
//     bit-identical to the pre-recorder binary.
//
// size_bytes is taken directly from p->GetSize() inside the callback.  No
// constant (1048, 1064, or otherwise) is ever substituted for it.
#ifndef TX_SERIALIZATION_RECORDER_H
#define TX_SERIALIZATION_RECORDER_H

#include <cstdio>
#include <string>
#include <ns3/packet.h>
#include <ns3/ptr.h>
#include <ns3/simulator.h>

namespace ns3 {

class TxSerializationRecorder {
public:
	// Returns true only when a path was supplied and the file opened.
	static bool Configure(const std::string &path, uint32_t nodeId,
			uint32_t ifIndex, uint32_t linkId,
			uint64_t windowStartNs, uint64_t windowEndNs)
	{
		if (path.empty())
			return false;          // default OFF: no file, no callbacks
		s_file = fopen(path.c_str(), "w");
		if (!s_file)
			return false;
		s_nodeId = nodeId;
		s_ifIndex = ifIndex;
		s_linkId = linkId;
		s_windowStartNs = windowStartNs;
		s_windowEndNs = windowEndNs;
		fprintf(s_file,
			"time_ns,event,node_id,ifindex,link_id,packet_uid,size_bytes\n");
		return true;
	}

	static void Close()
	{
		if (s_file) {
			fclose(s_file);
			s_file = 0;
		}
	}

	// Bound callbacks.  The trace source signature is Ptr<const Packet>, which
	// also makes the read-only property explicit at the type level.
	static void TxBegin(Ptr<const Packet> p) { Record("TX_BEGIN", p); }
	static void TxEnd(Ptr<const Packet> p) { Record("TX_END", p); }

	static uint64_t Recorded() { return s_recorded; }

private:
	static void Record(const char *event, Ptr<const Packet> p)
	{
		if (!s_file || !p)
			return;
		const uint64_t now = Simulator::Now().GetTimeStep();
		// Guard band: the evaluation window is widened so a packet that began
		// serializing just before windowStart, or finishes just after
		// windowEnd, is still captured whole.  Without it the first and last
		// windows would be missing packets and R-1b's Lmax would be wrong.
		if (s_windowEndNs > 0 &&
				(now + s_guardNs < s_windowStartNs ||
				 now > s_windowEndNs + s_guardNs))
			return;
		fprintf(s_file, "%lu,%s,%u,%u,%u,%lu,%u\n",
			(unsigned long)now, event, s_nodeId, s_ifIndex, s_linkId,
			(unsigned long)p->GetUid(),
			(unsigned)p->GetSize());   // the REAL wire size, never a constant
		s_recorded++;
	}

	static FILE *s_file;
	static uint32_t s_nodeId, s_ifIndex, s_linkId;
	static uint64_t s_windowStartNs, s_windowEndNs, s_recorded;
	// Two maximum-size serializations at 10 Gbps: 2 * 1500 B * 8 / 1e10 = 2.4 us.
	// Rounded up generously; a guard band only ever ADDS rows.
	static const uint64_t s_guardNs = 5000;
};

} // namespace ns3

#endif // TX_SERIALIZATION_RECORDER_H
