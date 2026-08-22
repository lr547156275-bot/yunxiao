// Pure-observation per-packet TX serialization recorder -- MULTI-LINK version.
//
// Supersedes tx-serialization-recorder.h (single-link, SHA 54a11a1d...,
// labelled SUPERSEDED_SINGLE_LINK_RECORDER).  That version attached only when
// selected_link_set.size() == 1, so S6 -- which has TWO bottlenecks, 84:1 and
// 83:1 -- would have silently produced an empty trace.
//
// Bypass guarantees, unchanged from the single-link version:
//   * Reads only the PhyTxBegin / PhyTxEnd trace sources QbbNetDevice already
//     fires (qbb-net-device.cc:464 and :261).
//   * Schedules, cancels and delays NOTHING.  No Simulator::Schedule / Cancel /
//     Remove appears in this file; only Simulator::Now(), read-only.
//   * Mutates no packet, device, queue or controller state.  The callback takes
//     Ptr<const Packet>.
//   * Default OFF: with no output path, Configure() registers nothing, opens no
//     file, and the run must be bit-identical to the pre-recorder binary.
//
// Multi-link identity:
//   Each (link_id, node_id, if_index) registers its OWN callback pair carrying
//   its own index, so an event's link identity comes from the registration --
//   not from inspecting the packet.  The same packet_uid can legitimately
//   appear on two bottlenecks; the pairing key is therefore
//   (link_id, node_id, if_index, packet_uid), and the checker groups by link
//   before evaluating any service curve.  Two independent 10 Gbps links are
//   never merged into one curve.
//
// packet_bytes always comes from p->GetSize().  No constant is substituted.
#ifndef TX_SERIALIZATION_RECORDER_ML_H
#define TX_SERIALIZATION_RECORDER_ML_H

#include <cstdio>
#include <string>
#include <vector>
#include <ns3/packet.h>
#include <ns3/ptr.h>
#include <ns3/simulator.h>

namespace ns3 {

class TxSerializationRecorderMl {
public:
	struct LinkKey {
		uint32_t linkId, nodeId, ifIndex;
		LinkKey() : linkId(0), nodeId(0), ifIndex(0) {}
		LinkKey(uint32_t l, uint32_t n, uint32_t i)
			: linkId(l), nodeId(n), ifIndex(i) {}
	};

	// Open the output file and set the evaluation window.  Returns false when
	// no path was given (default OFF) or the file cannot be created.
	static bool Open(const std::string &path, uint64_t windowStartNs,
			uint64_t windowEndNs)
	{
		if (path.empty())
			return false;
		s_file = fopen(path.c_str(), "w");
		if (!s_file)
			return false;
		s_windowStartNs = windowStartNs;
		s_windowEndNs = windowEndNs;
		fprintf(s_file, "time_ns,event,link_id,node_id,if_index,"
			"packet_uid,packet_bytes\n");
		return true;
	}

	// Register one bottleneck.  Returns the slot index to bind callbacks with;
	// a duplicate (link_id,node_id,if_index) is rejected with -1 so a double
	// attach cannot silently double-count.
	static int Register(uint32_t linkId, uint32_t nodeId, uint32_t ifIndex)
	{
		for (uint32_t i = 0; i < s_links.size(); ++i)
			if (s_links[i].linkId == linkId &&
					s_links[i].nodeId == nodeId &&
					s_links[i].ifIndex == ifIndex)
				return -1;                 // duplicate registration
		s_links.push_back(LinkKey(linkId, nodeId, ifIndex));
		return (int)s_links.size() - 1;
	}

	static uint32_t LinkCount() { return (uint32_t)s_links.size(); }
	static uint64_t Recorded() { return s_recorded; }
	static uint64_t RecordedOn(uint32_t slot)
	{
		return slot < s_perLink.size() ? s_perLink[slot] : 0;
	}
	static bool IsOpen() { return s_file != 0; }

	static void Close()
	{
		if (s_file) {
			fclose(s_file);
			s_file = 0;
		}
	}

	// Bound per-slot callbacks.  The slot carries the link identity, so no
	// packet inspection is needed to know which bottleneck an event is on.
	static void TxBegin(uint32_t slot, Ptr<const Packet> p)
	{
		Record(slot, "TX_BEGIN", p);
	}
	static void TxEnd(uint32_t slot, Ptr<const Packet> p)
	{
		Record(slot, "TX_END", p);
	}

private:
	static void Record(uint32_t slot, const char *event, Ptr<const Packet> p)
	{
		if (!s_file || !p || slot >= s_links.size())
			return;
		const uint64_t now = Simulator::Now().GetTimeStep();
		// Guard band so a packet already serializing when the window opens, or
		// still serializing when it closes, is not half-captured.  A guard only
		// ever ADDS rows; the checker classifies them as leading/trailing.
		if (s_windowEndNs > 0 &&
				(now + s_guardNs < s_windowStartNs ||
				 now > s_windowEndNs + s_guardNs))
			return;
		const LinkKey &k = s_links[slot];
		fprintf(s_file, "%lu,%s,%u,%u,%u,%lu,%u\n",
			(unsigned long)now, event, k.linkId, k.nodeId, k.ifIndex,
			(unsigned long)p->GetUid(),
			(unsigned)p->GetSize());   // REAL wire size, never a constant
		s_recorded++;
		if (s_perLink.size() <= slot)
			s_perLink.resize(slot + 1, 0);
		s_perLink[slot]++;
	}

	static FILE *s_file;
	static std::vector<LinkKey> s_links;
	static std::vector<uint64_t> s_perLink;
	static uint64_t s_windowStartNs, s_windowEndNs, s_recorded;
	static const uint64_t s_guardNs = 5000;
};

} // namespace ns3

#endif // TX_SERIALIZATION_RECORDER_ML_H
