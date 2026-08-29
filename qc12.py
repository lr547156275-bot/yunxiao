import io
ph='/work/simulation/src/point-to-point/model/rdma-hw.h'
h=io.open(ph,encoding='utf-8',errors='surrogateescape').read()
decl='''	// One control epoch of the queue-bounded controller.  Provably inert when
	// queueControllerEnable is false (early return before any state change).
	static void QueueControllerEpoch(CbapLinkRuntime &runtime,
		uint64_t nowNs, uint64_t queueBytes, uint64_t rEffectiveBps,
		uint64_t pendingExcessBytes, uint32_t activeSenders,
		bool pfcSafe, uint64_t ledgerCountedBurstBytes,
		uint64_t minRateBps);
'''
assert h.count(decl)==1, h.count(decl)
h=h.replace(decl,'')     # remove from line 790 (before the struct exists)
tgt='''	static uint64_t ComputeDelayCreditBudget(CbapLinkRuntime &runtime,
		uint64_t queueBytes, uint32_t newFlowCount, uint64_t nowNs,
		uint32_t epoch, CbapDelayCreditRecord *out);'''
assert h.count(tgt)==1
h=h.replace(tgt, tgt+'\n'+decl)
io.open(ph,'w',encoding='utf-8',errors='surrogateescape').write(h)
i_struct=h.index('struct CbapLinkRuntime')
i_decl=h.index('QueueControllerEpoch')
print("struct at %d, decl at %d -> decl is %s struct"
      % (i_struct, i_decl, "AFTER" if i_decl>i_struct else "BEFORE (bad)"))
