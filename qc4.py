import io
pc='/work/simulation/src/point-to-point/model/rdma-hw.cc'
c=io.open(pc,encoding='utf-8',errors='surrogateescape').read()
assert c.count("QueueControllerEpoch(runtime")==0

a='''	record.effectiveCapacityBps =
		(uint64_t)std::floor(effective);'''
assert c.count(a)==1
ins = r'''	// Queue-bounded boost/drain controller (method D).  Separate from the
	// EXPERIMENTAL credit path above: its own flag, its own state, and it never
	// runs together with it -- delayCreditEnable and queueControllerEnable are
	// mutually exclusive by preflight assertion in third.cc.
	//
	// Ordered after the flow census for the same reason the credit call is: the
	// packetization margin scales with the active sender count.
	if (s_cbapConfig.queueControllerEnable) {
		uint32_t nActive = record.activeControlledFlows +
			record.pendingControlledFlows;
		// R_effective: the rate senders are ACTUALLY pacing at, summed over
		// controlled flows on this link.  Never a commanded-but-unconfirmed
		// value -- that is the prohibition the contract turns on.
		uint64_t rEffective = 0;
		uint64_t minRateBps = 0;
		for (std::map<uint32_t, CbapFlowRuntime>::const_iterator flow =
				s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow) {
			if (!flow->second.active || flow->second.finished ||
					!flow->second.qp || !flow->second.hw)
				continue;
			const std::vector<uint32_t> &path = s_cbapFlowPaths[flow->first];
			if (std::find(path.begin(), path.end(), linkId) == path.end())
				continue;
			rEffective += flow->second.qp->m_rate.GetBitRate();
			if (minRateBps == 0)
				minRateBps = flow->second.hw->m_minRate.GetBitRate();
		}
		rEffective += runtime.config.backgroundBps;
		const bool pfcSafe = !snapshot.localPaused &&
			!snapshot.downstreamPaused;
		QueueControllerEpoch(runtime, record.deliveryTimeNs,
			record.queueBytes, rEffective, 0, nActive, pfcSafe, 0,
			minRateBps);
		// Apply the resulting absolute target.  sumR = C + boost - drain.
		long double target = (long double)snapshot.capacityBps +
			(long double)runtime.qcBoostEffectiveBps -
			(long double)runtime.qcDrainTargetBps;
		long double credited = target -
			(long double)runtime.config.backgroundBps;
		effective = std::max(0.0L, credited);
	}
''' + a
c=c.replace(a, ins)
io.open(pc,'w',encoding='utf-8',errors='surrogateescape').write(c)
print("call site inserted:", c.count("QueueControllerEpoch(runtime"))
