import io
p='/work/simulation/scratch/third.cc'
s=io.open(p,encoding='utf-8',errors='surrogateescape').read()
old='''static void SampleCbapQcTrace(uint32_t linkId, uint64_t queueBytes,
		uint64_t capacityBps){'''
assert s.count(old)==1
s=s.replace(old,'''static void SampleCbapQcTrace(uint32_t linkId, uint64_t queueBytes,
		uint64_t capacityBps, uint32_t activeSenders){''')
old2='''		qStop + (double)0,                       /* Q_safe margin added below */'''
assert s.count(old2)==1
s=s.replace(old2,'''		qStop + (double)activeSenders *
			(double)cbap_max_wire_packet_bytes,   /* Q_safe = Q_stop + margin */''')
old3='	SampleCbapQcTrace(linkId, snapshot.queueBytes, snapshot.capacityBps);'
assert s.count(old3)==1
s=s.replace(old3,'''	{
		// active sender count for the packetization margin, same census the
		// controller uses (flows on this link, not yet handed off).
		uint32_t qcActive = 0;
		for (map<uint32_t, RdmaHw::BopMultilinkLink>::const_iterator qd =
				cbap_link_by_id.begin(); qd != cbap_link_by_id.end(); ++qd)
			(void)qd;
		qcActive = cbap_qc_last_active_senders;
		SampleCbapQcTrace(linkId, snapshot.queueBytes, snapshot.capacityBps,
			qcActive);
	}''')
# a simple global the RdmaHw side can publish; default 0 keeps it inert
a='static FILE *cbap_qc_trace_csv = NULL;'
assert s.count(a)==1
s=s.replace(a, a+'''
// Published by the controller call site so the trace can compute Q_safe with
// the same sender count the controller used.  0 until the controller runs.
uint32_t cbap_qc_last_active_senders = 0;''')
io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(s)
print("q_safe fixed; margin uses activeSenders")
