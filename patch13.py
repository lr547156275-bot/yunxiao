import io
# --- add the read-only QP accessor ---
ph='/work/simulation/src/point-to-point/model/rdma-hw.h'
h=io.open(ph,encoding='utf-8',errors='surrogateescape').read()
if h.count("GetCbapQpForAudit")==0:
    a='	static void (*s_cbapActuationHook)(uint32_t, uint64_t, uint64_t);'
    assert h.count(a)==1
    h=h.replace(a, a+'''
	// Read-only: the QP behind a CBAP flow id, for audit correlation only.
	// Returns NULL if the flow is unknown.  Const-correct by contract: callers
	// must not mutate through it, and no control path uses this accessor.
	static Ptr<RdmaQueuePair> GetCbapQpForAudit(uint32_t flowId);''')
    io.open(ph,'w',encoding='utf-8',errors='surrogateescape').write(h)

pc='/work/simulation/src/point-to-point/model/rdma-hw.cc'
c=io.open(pc,encoding='utf-8',errors='surrogateescape').read()
if c.count("RdmaHw::GetCbapQpForAudit")==0:
    a2='void (*RdmaHw::s_cbapActuationHook)(uint32_t, uint64_t, uint64_t) = NULL;'
    assert c.count(a2)==1
    c=c.replace(a2, a2+'''

Ptr<RdmaQueuePair> RdmaHw::GetCbapQpForAudit(uint32_t flowId)
{
	std::map<uint32_t, CbapFlowRuntime>::const_iterator it =
		s_cbapFlows.find(flowId);
	if (it == s_cbapFlows.end())
		return NULL;
	return it->second.qp;
}''')
    io.open(pc,'w',encoding='utf-8',errors='surrogateescape').write(c)
print("accessor: declared=%d defined=%d" % (h.count("GetCbapQpForAudit"),
                                            c.count("RdmaHw::GetCbapQpForAudit")))
