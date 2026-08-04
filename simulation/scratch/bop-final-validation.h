#ifndef BOP_FINAL_VALIDATION_H
#define BOP_FINAL_VALIDATION_H

#include "ns3/core-module.h"
#include "ns3/custom-header.h"
#include "ns3/qbb-net-device.h"
#include "ns3/rdma-queue-pair.h"
#include "ns3/prt-probe-tag.h"
#include <algorithm>
#include <cstdio>
#include <limits>
#include <map>
#include <vector>

namespace BopFinalValidation {

using ns3::CustomHeader;
using ns3::Ptr;
using ns3::QbbNetDevice;
using ns3::RdmaQueuePair;
using ns3::PrtProbeTag;

struct Config {
	bool enabled;
	uint32_t bottleneckNode;
	uint32_t bottleneckIf;
	uint32_t collectiveFlowCount;
	uint32_t packetPayloadBytes;
	uint32_t paddingBytes;
	std::string algorithm;
	std::string outputFile;
	Config()
		: enabled(false), bottleneckNode(0), bottleneckIf(0),
		  collectiveFlowCount(0), packetPayloadBytes(0), paddingBytes(0) {}
};

struct FlowKey {
	uint32_t sip, dip;
	uint16_t sport, dport, pg;
	bool operator<(const FlowKey &other) const {
		if (sip != other.sip) return sip < other.sip;
		if (dip != other.dip) return dip < other.dip;
		if (sport != other.sport) return sport < other.sport;
		if (dport != other.dport) return dport < other.dport;
		return pg < other.pg;
	}
};

struct RoundRange {
	uint32_t roundId;
	uint64_t begin, end;
};

struct FlowSpec {
	uint32_t flowId;
	std::vector<RoundRange> rounds;
};

struct WireAggregate {
	uint64_t packetCount;
	uint64_t payloadBytes;
	uint64_t wireBytes;
	uint32_t minimumWireBytes;
	uint32_t maximumWireBytes;
	uint32_t headerOverheadBytes;
	bool overheadInitialized;
	WireAggregate()
		: packetCount(0), payloadBytes(0), wireBytes(0),
		  minimumWireBytes(std::numeric_limits<uint32_t>::max()),
		  maximumWireBytes(0), headerOverheadBytes(0),
		  overheadInitialized(false) {}
};

static Config g_config;
static std::map<FlowKey, FlowSpec> g_flows;
static std::map<std::pair<uint32_t, uint32_t>, WireAggregate> g_wire;

inline void Configure(const Config &config) {
	g_config = config;
}

inline void RegisterFlow(uint32_t flowId, uint32_t sip, uint32_t dip,
		uint16_t sport, uint16_t dport, uint16_t pg,
		const std::vector<RdmaQueuePair::CrfmRoundState> &rounds) {
	if (!g_config.enabled || flowId >= g_config.collectiveFlowCount)
		return;
	FlowSpec flow;
	flow.flowId = flowId;
	uint64_t sequence = 0;
	for (uint32_t index = 0; index < rounds.size(); ++index) {
		RoundRange range = {rounds[index].roundId, sequence,
			sequence + rounds[index].roundBytes};
		sequence = range.end;
		flow.rounds.push_back(range);
	}
	FlowKey key = {sip, dip, sport, dport, pg};
	std::pair<std::map<FlowKey, FlowSpec>::iterator, bool> inserted =
		g_flows.insert(std::make_pair(key, flow));
	NS_ASSERT_MSG(inserted.second,
			"duplicate BOP final-validation flow key");
}

inline void BottleneckTxBegin(Ptr<QbbNetDevice> device,
		Ptr<const ns3::Packet> packet) {
	if (!g_config.enabled ||
			device->GetNode()->GetId() != g_config.bottleneckNode ||
			device->GetIfIndex() != g_config.bottleneckIf)
		return;
	// A PRT probe deliberately reuses the collective five tuple and sequence
	// position, but carries no application payload.  It remains on the real
	// wire and in the real queue; only this payload/wire accounting observer
	// must exclude it.
	PrtProbeTag probe;
	if (packet->PeekPacketTag(probe))
		return;
	CustomHeader header(CustomHeader::L2_Header | CustomHeader::L3_Header |
		CustomHeader::L4_Header);
	header.getInt = 1;
	packet->PeekHeader(header);
	if (header.l3Prot != 0x11)
		return;
	FlowKey key = {header.sip, header.dip, header.udp.sport,
		header.udp.dport, header.udp.pg};
	std::map<FlowKey, FlowSpec>::iterator found = g_flows.find(key);
	if (found == g_flows.end())
		return; // primer or unrelated DATA
	const RoundRange *range = NULL;
	for (uint32_t index = 0; index < found->second.rounds.size(); ++index)
		if (header.udp.seq >= found->second.rounds[index].begin &&
				header.udp.seq < found->second.rounds[index].end) {
			range = &found->second.rounds[index];
			break;
		}
	NS_ASSERT_MSG(range != NULL, "collective DATA sequence is outside rounds");
	uint32_t payload = (uint32_t)std::min(
		(uint64_t)g_config.packetPayloadBytes,
		range->end - header.udp.seq);
	uint32_t wire = packet->GetSize();
	NS_ASSERT_MSG(wire >= payload + g_config.paddingBytes,
			"wire DATA is smaller than payload plus padding");
	uint32_t overhead = wire - payload - g_config.paddingBytes;
	WireAggregate &value = g_wire[std::make_pair(
		found->second.flowId, range->roundId)];
	if (value.overheadInitialized)
		NS_ASSERT_MSG(value.headerOverheadBytes == overhead,
				"DATA header overhead changes within flow-round");
	else {
		value.headerOverheadBytes = overhead;
		value.overheadInitialized = true;
	}
	value.packetCount++;
	value.payloadBytes += payload;
	value.wireBytes += wire;
	value.minimumWireBytes = std::min(value.minimumWireBytes, wire);
	value.maximumWireBytes = std::max(value.maximumWireBytes, wire);
}

inline void WriteOutputs() {
	if (!g_config.enabled)
		return;
	FILE *output = fopen(g_config.outputFile.c_str(), "w");
	NS_ASSERT_MSG(output != NULL,
			"cannot open final-validation wire summary");
	fprintf(output,
		"algorithm,flow_id,round_id,packet_count,"
		"application_payload_bytes,mean_wire_data_bytes,"
		"min_wire_data_bytes,max_wire_data_bytes,"
		"header_overhead_bytes,padding_bytes\n");
	for (std::map<std::pair<uint32_t, uint32_t>, WireAggregate>::iterator it =
			g_wire.begin(); it != g_wire.end(); ++it) {
		const WireAggregate &value = it->second;
		fprintf(output, "%s,%u,%u,%lu,%lu,%.6f,%u,%u,%u,%u\n",
			g_config.algorithm.c_str(), it->first.first, it->first.second,
			value.packetCount, value.payloadBytes,
			value.packetCount ? (double)value.wireBytes /
				value.packetCount : 0,
			value.minimumWireBytes, value.maximumWireBytes,
			value.headerOverheadBytes, g_config.paddingBytes);
	}
	fclose(output);
}

} // namespace BopFinalValidation

#endif /* BOP_FINAL_VALIDATION_H */
