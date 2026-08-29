import io

pc = '/work/simulation/src/point-to-point/model/rdma-hw.cc'
c = io.open(pc, encoding='utf-8', errors='surrogateescape').read()
start = c.index('void RdmaHw::QueueControllerEpoch')
nxt = c.find('\nuint64_t RdmaHw::', start)
assert nxt > start

new = r'''void RdmaHw::QueueControllerEpoch(CbapLinkRuntime &runtime, uint64_t nowNs,
		uint64_t queueBytes, uint64_t rEffectiveBps,
		uint64_t pendingExcessBytes, uint32_t activeSenders, bool pfcSafe,
		uint64_t inFlightArrivalBytes, uint64_t minRateBps)
{
	// Gate 1: provably inert when disabled -- returns before touching state.
	if (!s_cbapConfig.queueControllerEnable)
		return;
	(void)rEffectiveBps;
	(void)pendingExcessBytes;
	(void)inFlightArrivalBytes;
	(void)minRateBps;
	// EVERYTHING below is in the WIRE domain: the queue, the link capacity and
	// the arrival rate all count wire bytes.  MIN_RATE is configured in the
	// PAYLOAD domain, so it is converted per QP before being summed.  Mixing
	// the two is what made a "6.5 G floor" never reconcile with a 10 G link.
	const long double cWire = (long double)runtime.config.capacityBps;
	if (cWire <= 0.0L || s_cbapConfig.qcHGuardS <= 0.0)
		return;

	// --- one queue sample per epoch, used for control AND for the trace ----
	runtime.qcQ0Bytes = queueBytes;
	runtime.qcEpochId++;
	const long double q0 = (long double)queueBytes;

	const long double hGuard = (long double)s_cbapConfig.qcHGuardS;
	const long double qAbs =
		(long double)s_cbapConfig.qcAppHardDelayS * cWire / 8.0L;
	const long double maxBoost =
		(long double)s_cbapConfig.qcMaxBoostRatio * cWire;
	const long double mAct = maxBoost * hGuard / 8.0L;
	const long double mSafe = (long double)s_cbapConfig.qcSafetyMarginBytes;
	const long double qRed = qAbs - mSafe;
	const long double qHigh = qRed - mAct;
	const long double qLow = (long double)s_cbapConfig.qcSoftFraction * qAbs;
	if (!(qLow > 0.0L && qLow < qHigh && qHigh < qRed && qRed < qAbs)) {
		runtime.qcBandInvalid = 1;
		return;
	}

	// --- ownership: no rates owned means no boost, no drain, DRAIN_MAX = 0 --
	// Previously, once the protected set emptied after the batch, the floor
	// collapsed and DRAIN_MAX approached C (~9.8 G of illegal drain权).
	if (!runtime.qcOwnsRates) {
		runtime.qcBoostEffectiveBps = 0;
		runtime.qcDrainTargetBps = 0;
		runtime.qcBoostCommandedBps = 0;
		runtime.qcDrainCommandedBps = 0;
		runtime.qcPendingGeneration = 0;
		runtime.qcDrainMaxWireBps = 0;
		runtime.qcFloorWireBps = 0;
		runtime.qcFloorPayloadBps = 0;
		runtime.qcZone = 0;
		runtime.qcQStopBytes = queueBytes;
		runtime.qcQSafeBytes = (uint64_t)(q0 + mSafe);
		return;
	}

	// --- floor from the UNIQUE protected set, per QP, converted to wire -----
	// floor_wire = sum over unique QPs of min_rate_payload * wire/payload.
	// No separate background term: the background QP is a member like any
	// other, and adding it twice is exactly what produced 6.600 G.
	long double floorPayload = 0.0L;
	long double floorWire = 0.0L;
	uint64_t dup = 0;
	std::set<uint32_t> seen;
	for (std::map<uint32_t, CbapQpLedger>::const_iterator it =
			runtime.qcLedger.begin(); it != runtime.qcLedger.end(); ++it) {
		if (!it->second.ownsRate)
			continue;
		if (!seen.insert(it->first).second) {
			dup++;
			continue;
		}
		const long double pay = (long double)it->second.minRatePayloadBps;
		const long double ratio = it->second.payloadPacketBytes > 0 ?
			(long double)it->second.wirePacketBytes /
			(long double)it->second.payloadPacketBytes : 1.0L;
		floorPayload += pay;
		floorWire += pay * ratio;
	}
	runtime.qcDuplicateQpCount = dup;
	runtime.qcFloorPayloadBps = (uint64_t)floorPayload;
	runtime.qcFloorWireBps = (uint64_t)floorWire;
	long double drainMax = cWire > floorWire ? cWire - floorWire : 0.0L;
	runtime.qcDrainMaxWireBps = (uint64_t)drainMax;

	const long double deadband =
		(long double)s_cbapConfig.qcOnWirePacketBytes * 8.0L / hGuard;

	// --- confirmation: a command whose deadline has passed becomes effective
	for (std::map<uint32_t, CbapQpLedger>::iterator it =
			runtime.qcLedger.begin(); it != runtime.qcLedger.end(); ++it) {
		if (it->second.commandedWireBps == 0 && !it->second.pendingUp &&
				!it->second.pendingDown)
			continue;
		if (nowNs >= it->second.effectDeadlineNs) {
			it->second.oldWireBps = it->second.commandedWireBps;
			it->second.senderEffectiveWireBps = it->second.commandedWireBps;
			it->second.predictedArrivalWireBps = it->second.commandedWireBps;
			it->second.pendingUp = false;
			it->second.pendingDown = false;
		}
	}
	if (runtime.qcPendingGeneration != 0 && nowNs >= runtime.qcPendingEtaNs) {
		runtime.qcBoostEffectiveBps = runtime.qcBoostCommandedBps;
		runtime.qcDrainTargetBps = runtime.qcDrainCommandedBps;
		runtime.qcActualEffectTimeNs = nowNs;
		runtime.qcBoostCommandedBps = 0;
		runtime.qcDrainCommandedBps = 0;
		runtime.qcPendingGeneration = 0;
		runtime.qcPendingEtaNs = 0;
	}

	// --- safe arrival envelope, per QP ------------------------------------
	// A pending SLOWDOWN may not be believed before its deadline: the
	// bottleneck is still receiving old-rate packets.  A pending SPEED-UP is
	// counted immediately, because that is the conservative direction.
	long double arrivalSafe = 0.0L;
	long double senderEff = 0.0L;
	long double arrivalAfterDeadline = 0.0L;
	uint64_t earliestDeadline = 0;
	for (std::map<uint32_t, CbapQpLedger>::const_iterator it =
			runtime.qcLedger.begin(); it != runtime.qcLedger.end(); ++it) {
		if (!it->second.ownsRate)
			continue;
		const long double oldR = (long double)it->second.oldWireBps;
		const long double cmdR = (long double)it->second.commandedWireBps;
		senderEff += (long double)it->second.senderEffectiveWireBps;
		if (it->second.pendingDown && nowNs < it->second.effectDeadlineNs) {
			// safe upper envelope: keep the OLD (higher) rate until deadline
			arrivalSafe += oldR > cmdR ? oldR : cmdR;
			arrivalAfterDeadline += cmdR;
			if (earliestDeadline == 0 ||
					it->second.effectDeadlineNs < earliestDeadline)
				earliestDeadline = it->second.effectDeadlineNs;
		} else if (it->second.pendingUp) {
			arrivalSafe += cmdR > oldR ? cmdR : oldR;
			arrivalAfterDeadline += cmdR > oldR ? cmdR : oldR;
		} else {
			arrivalSafe += it->second.predictedArrivalWireBps;
			arrivalAfterDeadline += it->second.predictedArrivalWireBps;
		}
	}
	runtime.qcArrivalSafeWireBps = (uint64_t)arrivalSafe;
	runtime.qcSenderEffectiveWireBps = (uint64_t)senderEff;

	// --- Q_stop as max prefix, starting AT tau = 0 (so Q_stop >= q0) -------
	long double tau = hGuard;
	if (earliestDeadline > nowNs) {
		tau = (long double)(earliestDeadline - nowNs) / 1e9L;
		if (tau > hGuard)
			tau = hGuard;
	}
	const long double q1 = q0 + (arrivalSafe - cWire) * tau / 8.0L;
	const long double q2 = q1 +
		(arrivalAfterDeadline - cWire) * (hGuard - tau) / 8.0L;
	long double qStop = q0;
	runtime.qcPrefixMaxIndex = 0;
	if (q1 > qStop) {
		qStop = q1;
		runtime.qcPrefixMaxIndex = 1;
	}
	if (q2 > qStop) {
		qStop = q2;
		runtime.qcPrefixMaxIndex = 2;
	}
	if (qStop < q0)
		runtime.qcInvariantViolations++;   // impossible by construction

	const long double qSafe = qStop + mSafe;
	runtime.qcQStopBytes = (uint64_t)qStop;
	runtime.qcQSafeBytes = (uint64_t)qSafe;
	if (qSafe > qAbs)
		runtime.qcQSafeOverAbs++;

	// --- zones, with the corrected RED hysteresis -------------------------
	bool pendingUpAny = false;
	for (std::map<uint32_t, CbapQpLedger>::const_iterator it =
			runtime.qcLedger.begin(); it != runtime.qcLedger.end(); ++it)
		if (it->second.ownsRate && it->second.pendingUp)
			pendingUpAny = true;
	const bool redEnter = (qSafe >= qAbs) || (q0 >= qAbs) || !pfcSafe;
	// Exit uses Q_stop and Q_current against Q_high directly.  Using
	// Q_safe < Q_high would subtract M_safe a SECOND time and held RED for
	// ~40 ms after the queue had already fallen below Q_high.
	const bool redExit = (qStop <= qHigh) && (q0 <= qHigh) && pfcSafe &&
		!pendingUpAny;
	uint32_t zone;
	if (redEnter || (runtime.qcInRed && !redExit))
		zone = 3;
	else if (qStop > qHigh)
		zone = 2;
	else if (qStop >= qLow)
		zone = 1;
	else
		zone = 0;
	runtime.qcInRed = (zone == 3);
	runtime.qcZone = zone;
	runtime.qcActiveSenders = activeSenders;

	if (zone == 3) {
		runtime.qcBoostCommandedBps = 0;
		runtime.qcDrainCommandedBps = (uint64_t)drainMax;
		runtime.qcBoostEffectiveBps = 0;
		runtime.qcDrainTargetBps = (uint64_t)drainMax;
		runtime.qcPendingGeneration = 0;
		runtime.qcPendingEtaNs = 0;
		return;
	}
	// After leaving RED, never jump straight back to BOOST while the batch is
	// still draining: zone 2/1 handle that, and exit recovery forbids upward.
	if (runtime.qcExitRecoveryPending && zone == 0)
		zone = 1;

	long double desired;
	if (zone == 2) {
		const long double span = qRed - qHigh;
		long double x = span > 0.0L ? (qStop - qHigh) / span : 1.0L;
		if (x < 0.0L)
			x = 0.0L;
		if (x > 1.0L)
			x = 1.0L;
		desired = -drainMax * x;
	} else if (zone == 1) {
		desired = 0.0L;
	} else {
		long double x = qLow > 0.0L ? (qLow - qStop) / qLow : 1.0L;
		if (x < 0.0L)
			x = 0.0L;
		if (x > 1.0L)
			x = 1.0L;
		desired = maxBoost * x;
	}
	if (runtime.qcExitRecoveryPending && desired > 0.0L)
		desired = 0.0L;               // no upward command during recovery
	if (desired < -drainMax)
		desired = -drainMax;
	if (cWire + desired < floorWire)
		desired = floorWire - cWire;

	const long double curU = (long double)runtime.qcBoostEffectiveBps -
		(long double)runtime.qcDrainTargetBps;
	if (runtime.qcPendingGeneration != 0) {
		const long double pend =
			(long double)runtime.qcBoostCommandedBps -
			(long double)runtime.qcDrainCommandedBps;
		if (desired < pend - deadband) {
			runtime.qcGenerationCounter++;
			runtime.qcRBeforeCommandBps = (uint64_t)(cWire + curU);
			runtime.qcBoostCommandedBps =
				(uint64_t)(desired > 0.0L ? desired : 0.0L);
			runtime.qcDrainCommandedBps =
				(uint64_t)(desired < 0.0L ? -desired : 0.0L);
			runtime.qcRCommandedBps = (uint64_t)(cWire + desired);
			runtime.qcPendingGeneration = runtime.qcGenerationCounter;
			runtime.qcCommandTimeNs = nowNs;
			runtime.qcPendingEtaNs = nowNs + (uint64_t)(hGuard * 1e9L);
			runtime.qcExpectedEffectTimeNs = runtime.qcPendingEtaNs;
		}
		return;
	}
	long double delta = desired - curU;
	if (delta < 0.0L)
		delta = -delta;
	if (delta < deadband)
		return;
	runtime.qcGenerationCounter++;
	runtime.qcRBeforeCommandBps = (uint64_t)(cWire + curU);
	runtime.qcBoostCommandedBps = (uint64_t)(desired > 0.0L ? desired : 0.0L);
	runtime.qcDrainCommandedBps = (uint64_t)(desired < 0.0L ? -desired : 0.0L);
	runtime.qcRCommandedBps = (uint64_t)(cWire + desired);
	runtime.qcPendingGeneration = runtime.qcGenerationCounter;
	runtime.qcCommandTimeNs = nowNs;
	runtime.qcPendingEtaNs = nowNs + (uint64_t)(hGuard * 1e9L);
	runtime.qcExpectedEffectTimeNs = runtime.qcPendingEtaNs;
}

'''

c = c[:start] + new + c[nxt:]
io.open(pc, 'w', encoding='utf-8', errors='surrogateescape').write(c)
print("controller: wire-domain floor from unique set, safe arrival envelope,")
print("            max-prefix from q0, RED exit on Q_stop/Q_current<=Q_high")
