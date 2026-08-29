import io

# --- header: rename the last parameter to match the .cc -------------------
ph = '/work/simulation/src/point-to-point/model/rdma-hw.h'
h = io.open(ph, encoding='utf-8', errors='surrogateescape').read()
old_decl = ('\t\tuint64_t pendingExcessBytes, uint32_t activeSenders,\n'
            '\t\tbool pfcSafe, uint64_t ledgerCountedBurstBytes,\n'
            '\t\tuint64_t minRateBps);')
if h.count(old_decl) == 1:
    h = h.replace(old_decl,
                  '\t\tuint64_t pendingExcessBytes, uint32_t activeSenders,\n'
                  '\t\tbool pfcSafe, uint64_t inFlightArrivalBytes,\n'
                  '\t\tuint64_t minRateBps);')
    io.open(ph, 'w', encoding='utf-8', errors='surrogateescape').write(h)
    print("header decl updated")
else:
    print("header decl already updated (count=%d)" % h.count(old_decl))

# --- call site -------------------------------------------------------------
pc = '/work/simulation/src/point-to-point/model/rdma-hw.cc'
c = io.open(pc, encoding='utf-8', errors='surrogateescape').read()

start = c.index('\tif (s_cbapConfig.queueControllerEnable) {')
end = c.index('\trecord.effectiveCapacityBps =', start)
old_block = c[start:end]

new_block = r'''	if (s_cbapConfig.queueControllerEnable) {
		uint32_t nActive = record.activeControlledFlows +
			record.pendingControlledFlows;
		// --- protected QP set: every controlled flow still present in the
		// rate target/effective vector on this link.  Membership is decided by
		// liveness, NOT by "did it send this epoch" -- a paced flow between
		// packets is still protected and its MIN_RATE still floors the drain.
		// Removed only on completion, reclaim or handoff.
		runtime.qcProtectedQps.clear();
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
			runtime.qcProtectedQps.insert(flow->first);
			// R_effective: the rate senders are ACTUALLY pacing at.
			rEffective += flow->second.qp->m_rate.GetBitRate();
			if (minRateBps == 0)
				minRateBps = flow->second.hw->m_minRate.GetBitRate();
		}
		rEffective += runtime.config.backgroundBps;
		if (minRateBps == 0)
			minRateBps = 100000000;

		// --- pending_excess_bytes, corrected.
		// It is NOT (boost - drain) * elapsed.  It is the extra bytes the OLD
		// effective rate keeps producing until a pending SLOWDOWN takes effect,
		// integrated over the REMAINING delay:
		//   pending_rate_delta      = R_effective_arrival - R_pending_arrival
		//   remaining_effect_delay  = clamp(effect_time - now, 0, H_guard)
		//   pending_excess_bytes    = max(0, delta) * remaining / 8
		// A pending SPEED-UP contributes nothing here (it is not a braking
		// delay) and the term can never be negative.
		uint64_t pendingExcess = 0;
		if (runtime.qcPendingGeneration != 0 &&
				runtime.qcPendingEtaNs > record.deliveryTimeNs) {
			const long double remaining =
				(long double)(runtime.qcPendingEtaNs -
					record.deliveryTimeNs) / 1e9L;
			const long double hGuard =
				(long double)s_cbapConfig.qcHGuardS;
			const long double rem = remaining > hGuard ? hGuard : remaining;
			const long double rEff =
				(long double)runtime.config.capacityBps +
				(long double)runtime.qcBoostEffectiveBps -
				(long double)runtime.qcDrainTargetBps;
			const long double rPend =
				(long double)runtime.config.capacityBps +
				(long double)runtime.qcBoostCommandedBps -
				(long double)runtime.qcDrainCommandedBps;
			runtime.qcRPendingBps = (uint64_t)rPend;
			const long double delta = rEff - rPend;
			if (delta > 0.0L)
				pendingExcess = (uint64_t)(delta * rem / 8.0L);
		}
		// in_flight_arrival_bytes is tracked separately from pending excess;
		// no measurement source is wired yet, so it is reported as 0 rather
		// than folded into another term.
		const uint64_t inFlight = 0;
		const bool pfcSafe = !snapshot.localPaused &&
			!snapshot.downstreamPaused;
		QueueControllerEpoch(runtime, record.deliveryTimeNs,
			record.queueBytes, rEffective, pendingExcess, nActive, pfcSafe,
			inFlight, minRateBps);
		long double target = (long double)snapshot.capacityBps +
			(long double)runtime.qcBoostEffectiveBps -
			(long double)runtime.qcDrainTargetBps;
		long double credited = target -
			(long double)runtime.config.backgroundBps;
		effective = std::max(0.0L, credited);
	}
'''

c = c[:start] + new_block + c[end:]
io.open(pc, 'w', encoding='utf-8', errors='surrogateescape').write(c)
print("call site rewritten: protected QP set + corrected pending excess")
