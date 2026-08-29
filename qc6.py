import io
NL=chr(92)+'n'
# --- expose the per-link controller state for the trace (read-only accessor) --
ph='/work/simulation/src/point-to-point/model/rdma-hw.h'
h=io.open(ph,encoding='utf-8',errors='surrogateescape').read()
if h.count("GetCbapQcStateForAudit")==0:
    a='	static Ptr<RdmaQueuePair> GetCbapQpForAudit(uint32_t flowId);'
    assert h.count(a)==1
    h=h.replace(a, a+'''
	// Read-only snapshot of the queue-controller state for one link, for the
	// trace only.  Returns false if the link is unknown.
	struct CbapQcSnapshot {
		uint64_t boostEffectiveBps, boostCommandedBps, pendingGeneration;
		uint64_t drainTargetBps, guardExceeded, queueBytes;
		uint32_t zone;
	};
	static bool GetCbapQcStateForAudit(uint32_t linkId, CbapQcSnapshot *out);''')
    io.open(ph,'w',encoding='utf-8',errors='surrogateescape').write(h)

pc='/work/simulation/src/point-to-point/model/rdma-hw.cc'
c=io.open(pc,encoding='utf-8',errors='surrogateescape').read()
if c.count("RdmaHw::GetCbapQcStateForAudit")==0:
    a2='''Ptr<RdmaQueuePair> RdmaHw::GetCbapQpForAudit(uint32_t flowId)'''
    assert c.count(a2)==1
    c=c.replace(a2,'''bool RdmaHw::GetCbapQcStateForAudit(uint32_t linkId, CbapQcSnapshot *out)
{
	std::map<uint32_t, CbapLinkRuntime>::const_iterator it =
		s_cbapLinks.find(linkId);
	if (it == s_cbapLinks.end() || !out)
		return false;
	out->boostEffectiveBps = it->second.qcBoostEffectiveBps;
	out->boostCommandedBps = it->second.qcBoostCommandedBps;
	out->pendingGeneration = it->second.qcPendingGeneration;
	out->drainTargetBps = it->second.qcDrainTargetBps;
	out->guardExceeded = it->second.qcGuardExceeded;
	out->queueBytes = it->second.latest.queueBytes;
	out->zone = it->second.qcZone;
	return true;
}

''' + a2)
    io.open(pc,'w',encoding='utf-8',errors='surrogateescape').write(c)
print("accessor: decl=%d def=%d" % (h.count("GetCbapQcStateForAudit"),
                                    c.count("RdmaHw::GetCbapQcStateForAudit")))
