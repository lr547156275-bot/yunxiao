import io, re
p='/work/simulation/scratch/third.cc'
src=io.open(p,encoding='utf-8',errors='surrogateescape').read()
NL=chr(92)+'n'

# --- 1) replace the whole old observer block with a generation-keyed design ---
start=src.index('// --- Actuation closed loop (read-only) ---')
end=src.index('// Sample every input of the real PFC predicate on the bottleneck switch.')
old_block=src[start:end]
assert 'CbapActuationOnRateCommand' in old_block

new_block = r'''// --- Actuation closed loop (read-only, generation-keyed) --------------------
// flowId alone cannot establish causality between the three stages, so every
// rate command gets a monotonically increasing command_generation, and the
// stages are correlated by (stable QP key, generation, packet sequence):
//
//   stage 1 rate_command   : generation G assigned; key = 5-tuple of the QP
//   stage 2 sender_effect  : first DATA scheduled UNDER the new rate; records
//                            the packet sequence (snd_nxt at dequeue)
//   stage 3 at_bottleneck  : the SAME (key, seq) observed at the bottleneck
//                            egress, matched back to G
//
// Nothing here reads back into a control decision: no rate, pacing, migration,
// replan or DCQCN path consults these structures.
struct CbapActuationKey {
	uint32_t sip, dip;
	uint16_t sport, dport;
	uint16_t pg;
	bool operator<(const CbapActuationKey &o) const {
		if (sip != o.sip) return sip < o.sip;
		if (dip != o.dip) return dip < o.dip;
		if (sport != o.sport) return sport < o.sport;
		if (dport != o.dport) return dport < o.dport;
		return pg < o.pg;
	}
};
struct CbapActuationPending {
	uint64_t generation;
	uint64_t commandNs;
	uint64_t rateBps;
	uint64_t flowId;
	bool senderSeen;
	uint64_t senderNs;
	uint64_t seq;          // sequence of the first packet under the new rate
	CbapActuationPending()
		: generation(0), commandNs(0), rateBps(0), flowId(0),
		  senderSeen(false), senderNs(0), seq(0) {}
};
static uint64_t cbap_actuation_generation = 0;
static map<CbapActuationKey, CbapActuationPending> cbap_actuation_pending;
// (key, seq) -> generation, awaiting the bottleneck sighting.
static map<pair<CbapActuationKey, uint64_t>, CbapActuationPending>
	cbap_actuation_inflight;
static uint64_t cbap_act_unmatched = 0, cbap_act_duplicate = 0,
	cbap_act_negative = 0;

static CbapActuationKey CbapKeyOfQp(Ptr<RdmaQueuePair> qp){
	CbapActuationKey k;
	k.sip = qp->sip; k.dip = qp->dip;
	k.sport = qp->sport; k.dport = qp->dport;
	k.pg = qp->m_pg;
	return k;
}

static void CbapActuationOnRateCommand(uint32_t flowId, uint64_t oldBps,
		uint64_t newBps){
	if (!cbap_actuation_csv)
		return;
	Ptr<RdmaQueuePair> qp = RdmaHw::GetCbapQpForAudit(flowId);
	if (!qp)
		return;
	CbapActuationKey k = CbapKeyOfQp(qp);
	CbapActuationPending pend;
	pend.generation = ++cbap_actuation_generation;
	pend.commandNs = Simulator::Now().GetTimeStep();
	pend.rateBps = newBps;
	pend.flowId = flowId;
	// A command that supersedes an unobserved earlier one for the same QP is a
	// dropped generation, counted rather than silently overwritten.
	if (cbap_actuation_pending.count(k))
		cbap_act_duplicate++;
	cbap_actuation_pending[k] = pend;
	fprintf(cbap_actuation_csv,
		"%lu,%lu,%lu,%lu,%lu,rate_command,0,0,0''' + NL + r'''",
		(unsigned long)pend.commandNs, (unsigned long)pend.generation,
		(unsigned long)flowId, (unsigned long)oldBps, (unsigned long)newBps);
}

// stage 2: the first packet this QP schedules after the command.
static void CbapActuationOnQpDequeue(Ptr<QbbNetDevice> device,
		Ptr<const Packet> packet, Ptr<RdmaQueuePair> qp){
	if (!cbap_actuation_csv || !qp)
		return;
	CbapActuationKey k = CbapKeyOfQp(qp);
	map<CbapActuationKey, CbapActuationPending>::iterator it =
		cbap_actuation_pending.find(k);
	if (it == cbap_actuation_pending.end())
		return;
	uint64_t now = Simulator::Now().GetTimeStep();
	if (now < it->second.commandNs){
		cbap_act_negative++;
		return;
	}
	CbapActuationPending pend = it->second;
	pend.senderSeen = true;
	pend.senderNs = now;
	// snd_nxt is the next byte to send; the packet just handed down starts here.
	pend.seq = qp->snd_nxt;
	cbap_actuation_pending.erase(it);
	cbap_actuation_inflight[make_pair(k, pend.seq)] = pend;
	fprintf(cbap_actuation_csv,
		"%lu,%lu,%lu,%lu,%lu,sender_rate_effect,%lu,0,%lu''' + NL + r'''",
		(unsigned long)now, (unsigned long)pend.generation,
		(unsigned long)pend.flowId, (unsigned long)0,
		(unsigned long)pend.rateBps,
		(unsigned long)(now - pend.commandNs), (unsigned long)pend.seq);
}

// stage 3: that same (key, seq) reaching the bottleneck egress.
static void CbapActuationAtBottleneck(uint32_t switchId, uint32_t inputPort,
		uint32_t outputPort, uint32_t qIndex, CustomHeader &ch){
	if (!cbap_actuation_csv)
		return;
	CbapActuationKey k;
	k.sip = ch.sip; k.dip = ch.dip;
	k.sport = ch.udp.sport; k.dport = ch.udp.dport;
	k.pg = ch.udp.pg;
	map<pair<CbapActuationKey, uint64_t>, CbapActuationPending>::iterator it =
		cbap_actuation_inflight.find(make_pair(k, (uint64_t)ch.udp.seq));
	if (it == cbap_actuation_inflight.end())
		return;                 // not a packet we are tracking
	uint64_t now = Simulator::Now().GetTimeStep();
	CbapActuationPending pend = it->second;
	cbap_actuation_inflight.erase(it);
	if (now < pend.senderNs){
		cbap_act_negative++;
		return;
	}
	fprintf(cbap_actuation_csv,
		"%lu,%lu,%lu,%lu,%lu,first_affected_at_bottleneck,%lu,%lu,%lu''' + NL + r'''",
		(unsigned long)now, (unsigned long)pend.generation,
		(unsigned long)pend.flowId, (unsigned long)0,
		(unsigned long)pend.rateBps,
		(unsigned long)(now - pend.senderNs),
		(unsigned long)(now - pend.commandNs), (unsigned long)pend.seq);
}

'''
src = src[:start] + new_block + src[end:]
io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(src)
print("observer block rewritten; generation-keyed:", src.count("cbap_actuation_generation"))
