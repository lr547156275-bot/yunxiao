import io
p='/work/simulation/scratch/third.cc'
src=io.open(p,encoding='utf-8',errors='surrogateescape').read()
NL=chr(92)+'n'
assert src.count("CbapActuationOnQpDequeue")==0, "already patched"

a='// Sample every input of the real PFC predicate on the bottleneck switch.'
assert src.count(a)==1
body='''// sender_rate_effect_time: the first packet to leave the QP whose rate was just
// commanded.  Bound to the sending device; identifies the flow via the QP.
static void CbapActuationOnQpDequeue(Ptr<QbbNetDevice> device,
		Ptr<const Packet> packet, Ptr<RdmaQueuePair> qp){
	if (!cbap_actuation_csv || !qp || cbap_pending_effect_flow == 0)
		return;
	if (qp->crfm.flowId != cbap_pending_effect_flow)
		return;
	if (cbap_last_sender_effect_ns != 0)
		return;                       // only the FIRST departure counts
	cbap_last_sender_effect_ns = Simulator::Now().GetTimeStep();
	cbap_pending_effect_bytes = packet ? packet->GetSize() : 0;
	fprintf(cbap_actuation_csv,
		"%lu,%lu,%lu,%lu,sender_rate_effect,%lu,0''' + NL + '''",
		(unsigned long)cbap_last_sender_effect_ns,
		(unsigned long)cbap_pending_effect_flow,
		(unsigned long)cbap_last_rate_cmd_bps,
		(unsigned long)cbap_pending_effect_bytes,
		(unsigned long)(cbap_last_sender_effect_ns - cbap_last_rate_cmd_ns));
}

// first_affected_packet_at_bottleneck_time: the first enqueue at the bottleneck
// egress at or after the sender effect.  Byte-size match is not attempted --
// the packet identity is not carried end to end -- so this is the first arrival
// after the effect, which is the quantity H_eff needs.
static void CbapActuationOnBottleneckEnqueue(Ptr<QbbNetDevice> device,
		Ptr<const Packet> packet, uint32_t qIndex){
	if (!cbap_actuation_csv || cbap_pending_effect_flow == 0)
		return;
	if (cbap_last_sender_effect_ns == 0)
		return;                       // no commanded packet has departed yet
	if (qIndex != cbap_priority)
		return;
	uint64_t now = Simulator::Now().GetTimeStep();
	fprintf(cbap_actuation_csv,
		"%lu,%lu,%lu,%lu,first_affected_at_bottleneck,%lu,%lu''' + NL + '''",
		(unsigned long)now, (unsigned long)cbap_pending_effect_flow,
		(unsigned long)cbap_last_rate_cmd_bps,
		(unsigned long)(packet ? packet->GetSize() : 0),
		(unsigned long)(now - cbap_last_sender_effect_ns),
		(unsigned long)(now - cbap_last_rate_cmd_ns));
	// One measurement per rate command; re-arm only on the next command.
	cbap_pending_effect_flow = 0;
	cbap_last_sender_effect_ns = 0;
}

'''
src=src.replace(a, body+a)
io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(src)
print("observers added:", src.count("CbapActuationOnQpDequeue"),
      src.count("CbapActuationOnBottleneckEnqueue"))
