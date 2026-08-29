import io
p='/work/simulation/scratch/third.cc'
s=io.open(p,encoding='utf-8',errors='surrogateescape').read()

# Remove the dead loop I left behind and read the sender count from the
# controller's own published state instead.
old='''	{
		// active sender count for the packetization margin, same census the
		// controller uses (flows on this link, not yet handed off).
		uint32_t qcActive = 0;
		for (map<uint32_t, RdmaHw::BopMultilinkLink>::const_iterator qd =
				cbap_link_by_id.begin(); qd != cbap_link_by_id.end(); ++qd)
			(void)qd;
		qcActive = cbap_qc_last_active_senders;
		SampleCbapQcTrace(linkId, snapshot.queueBytes, snapshot.capacityBps,
			qcActive);
	}'''
assert s.count(old)==1
s=s.replace(old,'''	SampleCbapQcTrace(linkId, snapshot.queueBytes, snapshot.capacityBps,
		cbap_qc_last_active_senders);''')
io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(s)
print("dead loop removed:", s.count("(void)qd;")==0)
