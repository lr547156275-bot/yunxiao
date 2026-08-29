import io

pc = '/work/simulation/src/point-to-point/model/rdma-hw.cc'
c = io.open(pc, encoding='utf-8', errors='surrogateescape').read()

start = c.index('\tif (s_cbapConfig.queueControllerEnable) {')
end = c.index('\trecord.effectiveCapacityBps =', start)

new = r'''	if (s_cbapConfig.queueControllerEnable) {
		uint32_t nActive = record.activeControlledFlows +
			record.pendingControlledFlows;
		// --- per-QP ledger, keyed by QP identity so the set is UNIQUE -------
		// The background flow is a member like any other: counting it again
		// through a separate term is what produced a 6.600 G floor where 65
		// unique QPs give 6.500 G payload / 6.812 G wire.
		const uint64_t payloadBytes = s_cbapConfig.packetPayloadBytes > 0 ?
			s_cbapConfig.packetPayloadBytes : 1000;
		const uint64_t wireBytes = s_cbapConfig.qcOnWirePacketBytes > 0 ?
			s_cbapConfig.qcOnWirePacketBytes : payloadBytes;
		std::set<uint32_t> live;
		for (std::map<uint32_t, CbapFlowRuntime>::const_iterator flow =
				s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow) {
			if (!flow->second.active || flow->second.finished ||
					!flow->second.qp || !flow->second.hw)
				continue;
			const std::vector<uint32_t> &path = s_cbapFlowPaths[flow->first];
			if (std::find(path.begin(), path.end(), linkId) == path.end())
				continue;
			live.insert(flow->first);
			CbapQpLedger &led = runtime.qcLedger[flow->first];
			led.ownsRate = true;
			led.minRatePayloadBps = flow->second.hw->m_minRate.GetBitRate();
			led.payloadPacketBytes = payloadBytes;
			led.wirePacketBytes = wireBytes;
			// Sender-effective, converted PAYLOAD -> WIRE once, here.
			const long double ratio = (long double)wireBytes /
				(long double)payloadBytes;
			const uint64_t senderWire = (uint64_t)((long double)
				flow->second.qp->m_rate.GetBitRate() * ratio);
			led.senderEffectiveWireBps = senderWire;
			if (led.oldWireBps == 0)
				led.oldWireBps = senderWire;
			if (!led.pendingUp && !led.pendingDown)
				led.predictedArrivalWireBps = senderWire;
		}
		// A QP leaves the ledger only on completion/reclaim, never because it
		// happened not to send this epoch.  While a last slowdown is still in
		// flight the entry is kept under exit recovery.
		for (std::map<uint32_t, CbapQpLedger>::iterator it =
				runtime.qcLedger.begin(); it != runtime.qcLedger.end(); ) {
			if (live.count(it->first)) {
				++it;
				continue;
			}
			if (it->second.pendingDown &&
					record.deliveryTimeNs < it->second.effectDeadlineNs) {
				it->second.exitRecoveryPending = true;
				++it;                      // keep: command not yet at the neck
				continue;
			}
			runtime.qcLedger.erase(it++);
		}
		runtime.qcProtectedQps = live;
		runtime.qcOwnsRates = !runtime.qcLedger.empty();
		runtime.qcExitRecoveryPending = false;
		for (std::map<uint32_t, CbapQpLedger>::const_iterator it =
				runtime.qcLedger.begin(); it != runtime.qcLedger.end(); ++it)
			if (it->second.exitRecoveryPending)
				runtime.qcExitRecoveryPending = true;

		const bool pfcSafe = !snapshot.localPaused &&
			!snapshot.downstreamPaused;
		QueueControllerEpoch(runtime, record.deliveryTimeNs,
			record.queueBytes, 0, 0, nActive, pfcSafe, 0, 0);

		// Propagate the aggregate absolute target into per-QP pending state so
		// the arrival envelope knows which direction each QP is moving.
		if (runtime.qcPendingGeneration != 0 &&
				runtime.qcCommandTimeNs == record.deliveryTimeNs) {
			const long double share = runtime.qcLedger.empty() ? 0.0L :
				(long double)(runtime.qcBoostCommandedBps -
					runtime.qcDrainCommandedBps) /
				(long double)runtime.qcLedger.size();
			for (std::map<uint32_t, CbapQpLedger>::iterator it =
					runtime.qcLedger.begin();
					it != runtime.qcLedger.end(); ++it) {
				if (!it->second.ownsRate)
					continue;
				// A pending SLOWDOWN must not be superseded by an upward
				// command: the old high rate is still arriving.
				if (it->second.pendingDown && share > 0.0L)
					continue;
				const long double target =
					(long double)it->second.senderEffectiveWireBps + share;
				it->second.generation = (uint32_t)runtime.qcPendingGeneration;
				it->second.commandTimeNs = runtime.qcCommandTimeNs;
				it->second.effectDeadlineNs = runtime.qcPendingEtaNs;
				it->second.commandedWireBps =
					(uint64_t)(target > 0.0L ? target : 0.0L);
				it->second.pendingUp = share > 0.0L;
				it->second.pendingDown = share < 0.0L;
			}
		}
		long double target = (long double)snapshot.capacityBps +
			(long double)runtime.qcBoostEffectiveBps -
			(long double)runtime.qcDrainTargetBps;
		// Convert the WIRE target back to the PAYLOAD domain exactly once,
		// at the boundary where it is handed to the senders.
		const long double ratio = (long double)wireBytes /
			(long double)payloadBytes;
		long double targetPayload = ratio > 0.0L ? target / ratio : target;
		long double credited = targetPayload -
			(long double)runtime.config.backgroundBps;
		effective = std::max(0.0L, credited);
	}
'''

c = c[:start] + new + c[end:]
io.open(pc, 'w', encoding='utf-8', errors='surrogateescape').write(c)
print("call site: unique per-QP ledger, wire<->payload once at the boundary")
print("packetPayloadBytes referenced: %d" % c.count('packetPayloadBytes'))
