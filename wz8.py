import io

p = '/work/simulation/scratch/third.cc'
s = io.open(p, encoding='utf-8', errors='surrogateescape').read()

# The trace recomputed q_stop with the OLD endpoint formula, independently of
# what QueueControllerEpoch stored. Proof in the data: a row with
# q_safe == q_stop (the trace never added M_safe) and
# q_current - q_stop == drain*H/8 exactly. So the reported violations were
# measurement artifacts. Read the controller's own values instead.
start = s.index('static void SampleCbapQcTrace')
end = s.index('\n}\n', start) + 3
new = r'''static void SampleCbapQcTrace(uint32_t linkId, uint64_t queueBytes,
		uint64_t capacityBps){
	if (!cbap_qc_trace_csv)
		return;
	RdmaHw::CbapQcSnapshot qc;
	if (!RdmaHw::GetCbapQcStateForAudit(linkId, &qc))
		return;
	const char *zone = qc.zone == 3 ? "RED" :
		(qc.zone == 2 ? "YELLOW-DRAIN" :
		 (qc.zone == 1 ? "YELLOW-HOLD" : "GREEN"));
	// sumR_effective = C + boost_effective - drain
	const double sumR = (double)capacityBps + (double)qc.boostEffectiveBps -
		(double)qc.drainTargetBps;
	// Q_stop and Q_safe come from the CONTROLLER, not recomputed here. An
	// earlier version recomputed q_stop with the old endpoint formula, which
	// made the trace report violations the controller never committed.
	fprintf(cbap_qc_trace_csv,
		"%lu,%u,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%.0f,%s,%lu,%lu,%lu,%lu,%lu,%lu\n",
		(unsigned long)Simulator::Now().GetTimeStep(), linkId,
		(unsigned long)queueBytes,
		(unsigned long)qc.qStopBytes,
		(unsigned long)qc.qSafeBytes,
		(unsigned long)qc.boostCommandedBps,
		(unsigned long)qc.boostEffectiveBps,
		(unsigned long)qc.drainTargetBps,
		(unsigned long)qc.pendingGeneration,
		sumR, zone,
		(unsigned long)qc.guardExceeded,
		(unsigned long)qc.floorBps,
		(unsigned long)qc.drainMaxBps,
		(unsigned long)qc.pendingExcessBytes,
		(unsigned long)qc.protectedCount,
		(unsigned long)qc.invariantViolations);
}
'''
s = s[:start] + new + s[end:]

old_hdr = ('\t\t\t\t"time_ns,link_id,q_current,q_stop,q_safe,boost_commanded,"\n'
           '\t\t\t\t"boost_effective,drain,pending_generation,sumR_effective,"\n'
           '\t\t\t\t"zone,guard_exceeded\\n");')
assert s.count(old_hdr) == 1, ('hdr', s.count(old_hdr))
s = s.replace(old_hdr,
              '\t\t\t\t"time_ns,link_id,q_current,q_stop,q_safe,boost_commanded,"\n'
              '\t\t\t\t"boost_effective,drain,pending_generation,sumR_effective,"\n'
              '\t\t\t\t"zone,guard_exceeded,floor_bps,drain_max_bps,"\n'
              '\t\t\t\t"pending_excess_bytes,protected_count,'
              'invariant_violations\\n");')

io.open(p, 'w', encoding='utf-8', errors='surrogateescape').write(s)
print("trace now reads controller state; columns=17")
