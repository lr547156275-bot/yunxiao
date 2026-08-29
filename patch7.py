import io
p='/work/simulation/scratch/third.cc'
src=io.open(p,encoding='utf-8',errors='surrogateescape').read()
NL=chr(92)+'n'
assert src.count("CbapActuationOnRateCommand")==0, "already patched"

# 1) the hook body + a bottleneck-side observer, inserted before ReadCbapPort
a='// Sample every input of the real PFC predicate on the bottleneck switch.'
assert src.count(a)==1
body='''// --- Actuation closed loop (read-only) --------------------------------------
// Three stages, each timestamped from the event that defines it rather than
// inferred from a sampled series:
//   rate_command_time                     : migration wrote a new pacing rate
//   sender_rate_effect_time               : that sender's next packet departs
//   first_affected_packet_at_bottleneck   : that packet is seen at the egress
// H_eff is then (first_affected_packet_at_bottleneck - queue_sample_time),
// where queue_sample_time is the telemetry sample that drove the decision.
static void CbapActuationOnRateCommand(uint32_t flowId, uint64_t oldBps,
		uint64_t newBps){
	cbap_last_rate_cmd_ns = Simulator::Now().GetTimeStep();
	cbap_last_rate_cmd_flow = flowId;
	cbap_last_rate_cmd_bps = newBps;
	cbap_last_sender_effect_ns = 0;
	cbap_pending_effect_flow = flowId;
	if (cbap_actuation_csv)
		fprintf(cbap_actuation_csv,
			"%lu,%u,%lu,%lu,rate_command,0,0''' + NL + '''",
			(unsigned long)cbap_last_rate_cmd_ns, flowId,
			(unsigned long)oldBps, (unsigned long)newBps);
}

'''
src=src.replace(a, body+a)

# 2) install the hook where the telemetry callback is registered
a2='			MakeCallback(&ReadCbapPort));'
assert src.count(a2)==1
src=src.replace(a2, a2+'''
	// Read-only audit hook; installed only when the trace file is requested.
	if (!cbap_actuation_file.empty())
		RdmaHw::s_cbapActuationHook = &CbapActuationOnRateCommand;''')
io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(src)
print("hook body + install:", src.count("CbapActuationOnRateCommand"))
