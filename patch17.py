import io
p='/work/simulation/scratch/third.cc'
src=io.open(p,encoding='utf-8',errors='surrogateescape').read()
NL=chr(92)+'n'

# 1) fix the supersession counter: it must count displaced PENDING entries, not
#    duplicate generations (which a ++counter makes impossible).
old='''	// A command that supersedes an unobserved earlier one for the same QP is a
	// dropped generation, counted rather than silently overwritten.
	if (cbap_actuation_pending.count(k))
		cbap_act_duplicate++;'''
assert src.count(old)==1
src=src.replace(old,'''	// A command that supersedes an unobserved earlier one for the same QP
	// displaces a pending entry.  Count THAT -- counting duplicate generations
	// would be vacuous, since generation is a monotonic ++counter.
	if (cbap_actuation_pending.count(k))
		cbap_act_superseded++;''')
src=src.replace('static uint64_t cbap_act_unmatched = 0, cbap_act_duplicate = 0,',
                'static uint64_t cbap_act_unmatched = 0, cbap_act_superseded = 0,')

# 2) add an ARRIVAL-side stage: the packet reaching the bottleneck ingress,
#    before egress queueing.  EgressDequeue fires at departure, which includes
#    the queue delay the controller is trying to predict -- so a horizon built on
#    it would double-count.  QbbEnqueue on the bottleneck device is the arrival.
a='// stage 3: that same (key, seq) reaching the bottleneck egress.'
assert src.count(a)==1
arr = r'''// stage 3a: the same (key, seq) ARRIVING at the bottleneck egress queue, i.e.
// before it waits there.  This -- not the dequeue instant -- is the correct
// endpoint for an actuation horizon, because the horizon is used to predict the
// very queue the packet is about to join.  Recorded separately from stage 3 so
// both are directly measured instead of one being inferred from the other.
static void CbapActuationAtBottleneckArrival(Ptr<const Packet> original,
		uint32_t qIndex){
	if (!cbap_actuation_csv || cbap_actuation_inflight.empty())
		return;
	if (qIndex != cbap_priority)
		return;
	Ptr<Packet> packet = original->Copy();
	CustomHeader ch(CustomHeader::L2_Header | CustomHeader::L3_Header |
		CustomHeader::L4_Header);
	ch.brief = 0;
	ch.getInt = 1;
	packet->PeekHeader(ch);
	if (ch.l3Prot != 0x11)
		return;
	CbapActuationKey k;
	k.sip = ch.sip; k.dip = ch.dip;
	k.sport = ch.udp.sport; k.dport = ch.udp.dport;
	k.pg = ch.udp.pg;
	map<pair<CbapActuationKey, uint64_t>, CbapActuationPending>::iterator it =
		cbap_actuation_inflight.find(make_pair(k, (uint64_t)ch.udp.seq));
	if (it == cbap_actuation_inflight.end())
		return;
	if (it->second.arrivalNs != 0)
		return;                       // only the first arrival
	uint64_t now = Simulator::Now().GetTimeStep();
	it->second.arrivalNs = now;
	fprintf(cbap_actuation_csv,
		"%lu,%lu,%lu,%lu,%lu,arrival_at_bottleneck,%lu,%lu,%lu''' + NL + r'''",
		(unsigned long)now, (unsigned long)it->second.generation,
		(unsigned long)it->second.flowId, (unsigned long)0,
		(unsigned long)it->second.rateBps,
		(unsigned long)(now - it->second.senderNs),
		(unsigned long)(now - it->second.commandNs),
		(unsigned long)ch.udp.seq);
}

'''
src=src.replace(a, arr+a)

# arrivalNs field
old_s='''	uint64_t seq;          // sequence of the first packet under the new rate'''
assert src.count(old_s)==1
src=src.replace(old_s, old_s+'''
	uint64_t arrivalNs;    // bottleneck ARRIVAL (before egress queueing)''')
old_i='''		  senderSeen(false), senderNs(0), seq(0) {}'''
assert src.count(old_i)==1
src=src.replace(old_i,'''		  senderSeen(false), senderNs(0), seq(0), arrivalNs(0) {}''')
io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(src)
print("arrival stage added:", src.count("CbapActuationAtBottleneckArrival"),
      "| superseded counter:", src.count("cbap_act_superseded"))
