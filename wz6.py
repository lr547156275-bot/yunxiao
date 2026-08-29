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
	const long double C = (long double)runtime.config.capacityBps;
	if (C <= 0.0L || s_cbapConfig.qcHGuardS <= 0.0)
		return;

	const long double hGuard = (long double)s_cbapConfig.qcHGuardS;
	// --- the four ordered boundaries: Q_low < Q_high < Q_red < Q_abs -----
	const long double qAbs =
		(long double)s_cbapConfig.qcAppHardDelayS * C / 8.0L;
	const long double maxBoost =
		(long double)s_cbapConfig.qcMaxBoostRatio * C;
	const long double mAct = maxBoost * hGuard / 8.0L;
	// M_safe = max(M_unc, M_pkt), NOT their sum: M_unc is a TOTAL residual
	// (actual peak minus predicted), so any packetization error is already
	// inside it.  Adding M_pkt would count the same bytes twice.
	const long double mSafe = (long double)s_cbapConfig.qcSafetyMarginBytes;
	const long double qRed = qAbs - mSafe;
	const long double qHigh = qRed - mAct;
	const long double qLow = (long double)s_cbapConfig.qcSoftFraction * qAbs;
	if (!(qLow > 0.0L && qLow < qHigh && qHigh < qRed && qRed < qAbs)) {
		runtime.qcBandInvalid = 1;
		return;
	}

	// --- DRAIN_MAX from the PROTECTED QP set ----------------------------
	// The floor must be the sum of minimum rates over every QP that would
	// actually receive this command -- not over whoever happened to send in
	// this epoch, and not a global historical peak.  A paced flow between
	// packets is still protected.
	//
	// The earlier instantaneous-count version collapsed the floor to
	// ~2*MIN_RATE in the completion tail, so DRAIN_MAX approached C: measured
	// drain 0.8151 C = 8.15 Gbps (2.3x the legal 3.5 G) in 88.7% of drain
	// epochs, sumR down to 1.849 G against a 6.5 G floor.
	long double floorBps = 0.0L;
	for (std::set<uint32_t>::const_iterator it =
			runtime.qcProtectedQps.begin();
			it != runtime.qcProtectedQps.end(); ++it) {
		std::map<uint32_t, CbapFlowRuntime>::const_iterator flow =
			s_cbapFlows.find(*it);
		if (flow == s_cbapFlows.end() || !flow->second.hw)
			continue;
		floorBps += (long double)flow->second.hw->m_minRate.GetBitRate();
	}
	if (floorBps <= 0.0L && minRateBps > 0)
		floorBps = (long double)minRateBps;   // degenerate: keep one floor
	long double drainMax = C > floorBps ? C - floorBps : 0.0L;
	if (drainMax < 0.0L)
		drainMax = 0.0L;
	runtime.qcFloorBps = (uint64_t)floorBps;
	runtime.qcDrainMaxBps = (uint64_t)drainMax;
	if (activeSenders > runtime.qcPeakActiveSenders)
		runtime.qcPeakActiveSenders = activeSenders;   // diagnostic only

	const long double deadband =
		(long double)s_cbapConfig.qcOnWirePacketBytes * 8.0L / hGuard;

	// --- confirmation: pending -> effective, then it PERSISTS ------------
	if (runtime.qcPendingGeneration != 0 && nowNs >= runtime.qcPendingEtaNs) {
		runtime.qcBoostEffectiveBps = runtime.qcBoostCommandedBps;
		runtime.qcDrainTargetBps = runtime.qcDrainCommandedBps;
		runtime.qcActualEffectTimeNs = nowNs;
		runtime.qcBoostCommandedBps = 0;
		runtime.qcDrainCommandedBps = 0;
		runtime.qcPendingGeneration = 0;
		runtime.qcPendingEtaNs = 0;
	}

	// --- Q_stop as the MAX PREFIX over [now, now + H_guard] --------------
	// q0 = Q_current; q1 = after the effective segment; q2 = after the pending
	// segment.  Q_stop = max(q0, q1, q2).  Q_stop >= Q_current then holds BY
	// CONSTRUCTION -- it is not a clamp bolted onto a wrong endpoint formula.
	// The endpoint formula was the actual defect: at the worst epoch it gave
	// Q_stop = 954,578 while Q_current was 1,132,888, a 178,310 B shortfall
	// exactly equal to drain * H_guard / 8, i.e. it subtracted FUTURE drain
	// from the queue that ALREADY exists.
	const long double uEff = (long double)runtime.qcBoostEffectiveBps -
		(long double)runtime.qcDrainTargetBps;
	long double tau = hGuard;
	long double uPend = uEff;
	if (runtime.qcPendingGeneration != 0 &&
			runtime.qcPendingEtaNs > nowNs) {
		tau = (long double)(runtime.qcPendingEtaNs - nowNs) / 1e9L;
		if (tau > hGuard)
			tau = hGuard;
		uPend = (long double)runtime.qcBoostCommandedBps -
			(long double)runtime.qcDrainCommandedBps;
	}
	const long double q0 = (long double)queueBytes +
		(long double)pendingExcessBytes + (long double)inFlightArrivalBytes;
	const long double q1 = q0 + uEff * tau / 8.0L;
	const long double q2 = q1 + uPend * (hGuard - tau) / 8.0L;
	long double qStop = q0;
	if (q1 > qStop)
		qStop = q1;
	if (q2 > qStop)
		qStop = q2;

	// Invariants.  A violation is a model error, so record it rather than
	// silently repairing the number.
	if (qStop < (long double)queueBytes)
		runtime.qcInvariantViolations++;

	const long double qSafe = qStop + mSafe;
	runtime.qcQStopBytes = (uint64_t)qStop;
	runtime.qcQSafeBytes = (uint64_t)qSafe;
	runtime.qcREffectiveBps = rEffectiveBps;
	runtime.qcPendingExcessBytes = pendingExcessBytes;
	runtime.qcInFlightArrivalBytes = inFlightArrivalBytes;
	if (qSafe > qAbs)
		runtime.qcQSafeOverAbs++;

	// --- zones ----------------------------------------------------------
	uint32_t zone;
	const bool redTrip = (qSafe >= qAbs) ||
		((long double)queueBytes >= qAbs) || !pfcSafe;
	if (redTrip || (runtime.qcInRed && qSafe >= qHigh))
		zone = 3;                    // RED, latched until Q_safe < Q_high
	else if (qStop > qHigh)
		zone = 2;                    // YELLOW-DRAIN
	else if (qStop >= qLow)
		zone = 1;                    // YELLOW-HOLD
	else
		zone = 0;                    // GREEN/BOOST
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
		desired = 0.0L;              // HOLD: sumR = C; migration continues
	} else {
		long double x = qLow > 0.0L ? (qLow - qStop) / qLow : 1.0L;
		if (x < 0.0L)
			x = 0.0L;
		if (x > 1.0L)
			x = 1.0L;
		desired = maxBoost * x;
	}
	// Hard clamps: drain may never exceed DRAIN_MAX, and the aggregate target
	// may never fall below the protected floor.
	if (desired < -drainMax)
		desired = -drainMax;
	if (C + desired < floorBps)
		desired = floorBps - C;

	const long double curU = (long double)runtime.qcBoostEffectiveBps -
		(long double)runtime.qcDrainTargetBps;
	if (runtime.qcPendingGeneration != 0) {
		const long double pend =
			(long double)runtime.qcBoostCommandedBps -
			(long double)runtime.qcDrainCommandedBps;
		if (desired < pend - deadband) {
			runtime.qcGenerationCounter++;
			runtime.qcRBeforeCommandBps = (uint64_t)(C + curU);
			runtime.qcBoostCommandedBps =
				(uint64_t)(desired > 0.0L ? desired : 0.0L);
			runtime.qcDrainCommandedBps =
				(uint64_t)(desired < 0.0L ? -desired : 0.0L);
			runtime.qcRCommandedBps = (uint64_t)(C + desired);
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
		return;                      // the working band IS the deadband
	runtime.qcGenerationCounter++;
	runtime.qcRBeforeCommandBps = (uint64_t)(C + curU);
	runtime.qcBoostCommandedBps = (uint64_t)(desired > 0.0L ? desired : 0.0L);
	runtime.qcDrainCommandedBps = (uint64_t)(desired < 0.0L ? -desired : 0.0L);
	runtime.qcRCommandedBps = (uint64_t)(C + desired);
	runtime.qcPendingGeneration = runtime.qcGenerationCounter;
	runtime.qcCommandTimeNs = nowNs;
	runtime.qcPendingEtaNs = nowNs + (uint64_t)(hGuard * 1e9L);
	runtime.qcExpectedEffectTimeNs = runtime.qcPendingEtaNs;
}

'''

c = c[:start] + new + c[nxt:]
io.open(pc, 'w', encoding='utf-8', errors='surrogateescape').write(c)
print("controller rewritten: max-prefix Q_stop, protected-QP floor, clamps")
