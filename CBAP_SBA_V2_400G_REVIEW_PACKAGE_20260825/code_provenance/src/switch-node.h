#ifndef SWITCH_NODE_H
#define SWITCH_NODE_H

#include <map>
#include <unordered_map>
#include <ns3/node.h>
#include "qbb-net-device.h"
#include "switch-mmu.h"
#include "pint.h"

namespace ns3 {

class Packet;

class SwitchNode : public Node{
	struct FixedPathKey {
		uint32_t sip;
		uint32_t dip;
		uint16_t sport;
		uint16_t dport;

		bool operator<(const FixedPathKey &other) const;
	};

	static const uint32_t pCnt = 257;	// Number of ports used
	static const uint32_t qCnt = 8;	// Number of queues/priorities used
	static bool UsesHpccInt(uint32_t ccMode);
	uint32_t m_ecmpSeed;
	std::unordered_map<uint32_t, std::vector<int> > m_rtTable; // map from ip address (u32) to possible ECMP port (index of dev)
	std::map<FixedPathKey, int> m_fixedPathTable; // optional exact-match forwarding rules for RDMA data

	// monitor of PFC
	uint32_t m_bytes[pCnt][pCnt][qCnt]; // m_bytes[inDev][outDev][qidx] is the bytes from inDev enqueued for outDev at qidx
	
	uint64_t m_txBytes[pCnt]; // counter of tx bytes
	uint64_t m_rxBytes[pCnt]; // cumulative bytes admitted to each egress
	uint64_t m_ecnMarks[pCnt];
	uint64_t m_pfcPauseEvents[pCnt];
	uint64_t m_pfcResumeEvents[pCnt];
	uint64_t m_pfcPauseStartNs[pCnt];
	uint64_t m_pfcPauseDurationNs[pCnt];

	uint32_t m_lastPktSize[pCnt];
	uint64_t m_lastPktTs[pCnt]; // ns
	double m_u[pCnt];

protected:
	bool m_ecnEnabled;
	bool m_pfcEnabled;
	uint32_t m_ccMode;
	uint64_t m_maxRtt;

	uint32_t m_ackHighPrio; // set high priority for ACK/NACK

private:
	int GetOutDev(Ptr<const Packet>, CustomHeader &ch);
	void SendToDev(Ptr<Packet>p, CustomHeader &ch);
	static uint32_t EcmpHash(const uint8_t* key, size_t len, uint32_t seed);
	void CheckAndSendPfc(uint32_t inDev, uint32_t qIndex);
	void CheckAndSendResume(uint32_t inDev, uint32_t qIndex);
public:
	Ptr<SwitchMmu> m_mmu;
	TracedCallback<uint32_t, uint32_t, uint32_t, uint32_t, uint32_t>
		m_tracePfcSemantic;
	TracedCallback<Ptr<const Packet>, uint32_t, uint32_t, uint32_t>
		m_traceEgressDequeue;

	static TypeId GetTypeId (void);
	SwitchNode();
	void SetEcmpSeed(uint32_t seed);
	void AddTableEntry(Ipv4Address &dstAddr, uint32_t intf_idx);
	bool AddFixedPathEntry(Ipv4Address sip, Ipv4Address dip, uint16_t sport, uint16_t dport, uint32_t intf_idx);
	uint64_t GetTxBytes(uint32_t intf_idx) const;
	uint64_t GetRxBytes(uint32_t intf_idx) const;
	uint64_t GetEcnMarks(uint32_t intf_idx) const;
	uint64_t GetPfcPauseEvents(uint32_t intf_idx) const;
	uint64_t GetPfcResumeEvents(uint32_t intf_idx) const;
	uint64_t GetPfcPauseDurationNs(uint32_t intf_idx) const;
	uint64_t GetEgressQueueBytes(uint32_t intf_idx) const;
	uint64_t GetEgressCapacityBps(uint32_t intf_idx) const;
	bool IsLocallyPaused(uint32_t intf_idx, uint32_t qIndex) const;
	bool IsDownstreamPaused(uint32_t intf_idx, uint32_t qIndex) const;
	void ClearTable();
	bool SwitchReceiveFromDevice(Ptr<NetDevice> device, Ptr<Packet> packet, CustomHeader &ch);
	void SwitchNotifyDequeue(uint32_t ifIndex, uint32_t qIndex, Ptr<Packet> p);

	// for approximate calc in PINT
	int logres_shift(int b, int l);
	int log2apprx(int x, int b, int m, int l); // given x of at most b bits, use most significant m bits of x, calc the result in l bits
};

} /* namespace ns3 */

#endif /* SWITCH_NODE_H */
