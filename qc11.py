import io
p='/work/simulation/scratch/third.cc'
s=io.open(p,encoding='utf-8',errors='surrogateescape').read()
# Use the snapshot's own activeSenders; drop the extra parameter and the global.
s=s.replace('''static void SampleCbapQcTrace(uint32_t linkId, uint64_t queueBytes,
		uint64_t capacityBps, uint32_t activeSenders){''',
'''static void SampleCbapQcTrace(uint32_t linkId, uint64_t queueBytes,
		uint64_t capacityBps){''')
s=s.replace('''		qStop + (double)activeSenders *
			(double)cbap_max_wire_packet_bytes,   /* Q_safe = Q_stop + margin */''',
'''		qStop + (double)qc.activeSenders *
			(double)cbap_max_wire_packet_bytes,   /* Q_safe = Q_stop + margin */''')
s=s.replace('''	SampleCbapQcTrace(linkId, snapshot.queueBytes, snapshot.capacityBps,
		cbap_qc_last_active_senders);''',
'''	SampleCbapQcTrace(linkId, snapshot.queueBytes, snapshot.capacityBps);''')
s=s.replace('''
// Published by the controller call site so the trace can compute Q_safe with
// the same sender count the controller used.  0 until the controller runs.
uint32_t cbap_qc_last_active_senders = 0;''','')
io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(s)
print("simplified: global removed=%s, uses qc.activeSenders=%s"
      % (s.count("cbap_qc_last_active_senders")==0,
         s.count("qc.activeSenders")==1))
