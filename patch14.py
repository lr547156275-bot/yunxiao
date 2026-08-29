import io
p='/work/simulation/scratch/third.cc'
src=io.open(p,encoding='utf-8',errors='surrogateescape').read()
NL=chr(92)+'n'

# Rewrite stage-3 to the real EgressDequeue signature, parsing the header itself.
old_start=src.index('// stage 3: that same (key, seq) reaching the bottleneck egress.')
old_end=src.index('// Sample every input of the real PFC predicate on the bottleneck switch.')
new = r'''// stage 3: that same (key, seq) reaching the bottleneck egress.  Signature
// matches SwitchNode's EgressDequeue trace source; the 5-tuple and sequence come
// from the packet, using the same parse idiom as the existing packet trace.
static void CbapActuationAtBottleneck(Ptr<const Packet> original,
		uint32_t inputPort, uint32_t outputPort, uint32_t qIndex){
	if (!cbap_actuation_csv || cbap_actuation_inflight.empty())
		return;
	if (qIndex != cbap_priority)
		return;
	if (!cbap_actuation_egress_valid ||
			outputPort != cbap_actuation_egress_if)
		return;
	Ptr<Packet> packet = original->Copy();
	CustomHeader ch(CustomHeader::L2_Header | CustomHeader::L3_Header |
		CustomHeader::L4_Header);
	ch.brief = 0;
	ch.getInt = 1;
	packet->PeekHeader(ch);
	if (ch.l3Prot != 0x11)
		return;                 // not UDP/RoCE data
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
		(unsigned long)(now - pend.commandNs), (unsigned long)ch.udp.seq);
}

'''
src = src[:old_start] + new + src[old_end:]

# the egress identity globals
a='static uint64_t cbap_actuation_generation = 0;'
assert src.count(a)==1
src=src.replace(a, a+'''
static bool cbap_actuation_egress_valid = false;
static uint32_t cbap_actuation_egress_if = 0;''')
io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(src)
print("stage3 rewritten to EgressDequeue signature")
