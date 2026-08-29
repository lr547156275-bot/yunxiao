import io
p='/work/simulation/scratch/third.cc'
s=io.open(p,encoding='utf-8',errors='surrogateescape').read()
NL=chr(92)+'n'
assert s.count("SampleCbapQcTrace")==0

# sampler, next to the PFC audit sampler (same tick, same read-only contract)
a='// Sample every input of the real PFC predicate on the bottleneck switch.'
assert s.count(a)==1
fn = r'''// Queue-controller trace.  Records every field item 9 requires so the two
// preflight runs can be audited without re-deriving anything.
static void SampleCbapQcTrace(uint32_t linkId, uint64_t queueBytes,
		uint64_t capacityBps){
	if (!cbap_qc_trace_csv)
		return;
	RdmaHw::CbapQcSnapshot qc;
	if (!RdmaHw::GetCbapQcStateForAudit(linkId, &qc))
		return;
	const char *zone = qc.zone == 2 ? "RED" : (qc.zone == 1 ? "YELLOW" : "GREEN");
	// sumR_effective = C + boost_effective - drain
	double sumR = (double)capacityBps + (double)qc.boostEffectiveBps -
		(double)qc.drainTargetBps;
	// Q_stop / Q_safe recomputed from the same inputs the controller used.
	double hGuard = cbap_qc_h_guard_us * 1e-6;
	double excess = (double)qc.boostEffectiveBps - (double)qc.drainTargetBps;
	if (qc.pendingGeneration != 0){
		double ep = (double)qc.boostCommandedBps - (double)qc.drainTargetBps;
		if (ep > excess)
			excess = ep;
	}
	double qStop = (double)queueBytes + excess * hGuard / 8.0;
	if (qStop < 0)
		qStop = 0;
	fprintf(cbap_qc_trace_csv,
		"%lu,%u,%lu,%.0f,%.0f,%lu,%lu,%lu,%lu,%.0f,%s,%lu''' + NL + r'''",
		(unsigned long)Simulator::Now().GetTimeStep(), linkId,
		(unsigned long)queueBytes, qStop,
		qStop + (double)0,                       /* Q_safe margin added below */
		(unsigned long)qc.boostCommandedBps,
		(unsigned long)qc.boostEffectiveBps,
		(unsigned long)qc.drainTargetBps,
		(unsigned long)qc.pendingGeneration,
		sumR, zone, (unsigned long)qc.guardExceeded);
}

'''
s=s.replace(a, fn+a)

# call it right after the PFC audit sample, same tick
b='	SampleCbapPfcAudit(linkId, snapshot.queueBytes);'
assert s.count(b)==1
s=s.replace(b, b+'''
	SampleCbapQcTrace(linkId, snapshot.queueBytes, snapshot.capacityBps);''')

# open the file
c='''	if (!cbap_pfc_ports_file.empty()){'''
assert s.count(c)==1
s=s.replace(c,'''	if (!cbap_qc_trace_file.empty()){
		cbap_qc_trace_csv = fopen(cbap_qc_trace_file.c_str(), "w");
		if (cbap_qc_trace_csv)
			fprintf(cbap_qc_trace_csv,
				"time_ns,link_id,q_current,q_stop,q_safe,boost_commanded,"
				"boost_effective,drain,pending_generation,sumR_effective,"
				"zone,guard_exceeded''' + NL + '''");
	}
''' + c)
io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(s)
print("trace: sampler=%d call=%d open=%d"
      % (s.count("static void SampleCbapQcTrace"),
         s.count("SampleCbapQcTrace(linkId"),
         s.count("cbap_qc_trace_csv = fopen")))
