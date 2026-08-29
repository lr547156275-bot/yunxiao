import io

pc = '/work/simulation/src/point-to-point/model/rdma-hw.cc'
c = io.open(pc, encoding='utf-8', errors='surrogateescape').read()
start = c.index('void RdmaHw::QueueControllerEpoch')
nxt = c.find('\nuint64_t RdmaHw::', start)
assert nxt > start

new = r'''void RdmaHw::QueueControllerEpoch(CbapLinkRuntime &runtime, uint64_t nowNs,
		uint64_t queueBytes, uint64_t rEffectiveBps,
		uint64_t pendingExcessBytes, uint32_t activeSenders, bool pfcSafe,
		uint64_t ledgerCountedBurstBytes, uint64_t minRateBps)
{
	// Gate 1: provably inert when disabled -- returns before touching state.
	if (!s_cbapConfig.queueControllerEnable)
		return;
	(void)rEffectiveBps;
	(void)ledgerCountedBurstBytes;
	const long double C = (long double)runtime.config.capacityBps;
	if (C <= 0.0L || s_cbapConfig.qcHGuardS <= 0.0 || minRateBps == 0)
		return;

	const long double hGuard = (long double)s_cbapConfig.qcHGuardS;
	// --- the four ordered boundaries: Q_low < Q_high < Q_red < Q_abs -----
	// Q_abs is an absolute ceiling (one message transmission time of queue),
	// NOT a set point the controller tries to hold.
	const long double qAbs =
		(long double)s_cbapConfig.qcAppHardDelayS * C / 8.0L;
	const long double maxBoost =
		(long double)s_cbapConfig.qcMaxBoostRatio * C;
	// M_act: queue one full boost can add within one guard window.
	const long double mAct = maxBoost * hGuard / 8.0L;
	// M_safe: measured prediction uncertainty plus the packet-granularity term
	// the predictor does not cover.  Configured, so it can be set from the
	// measured residual instead of guessed in code.
	const long double mSafe = (long double)s_cbapConfig.qcSafetyMarginBytes;
	const long double qRed = qAbs - mSafe;
	const long double qHigh = qRed - mAct;
	const long double qLow = (long double)s_cbapConfig.qcSoftFraction * qAbs;
	if (!(qLow > 0.0L && qLow < qHigh && qHigh < qRed && qRed < qAbs)) {
		// A collapsed band is a configuration error, never silently truncated.
		runtime.qcBandInvalid = 1;
		return;
	}

	// --- DRAIN_MAX from the REAL flow floor -----------------------------
	// Bug fixed here.  An earlier version scaled the floor by the INSTANTANEOUS
	// activeSenders, which collapses to ~2*MIN_RATE in the completion tail;
	// DRAIN_MAX then approached C.  Measured consequence: drain reached
	// 0.8151 C = 8.15 Gbps (2.3x the legal 3.5 G) in 88.7% of drain epochs,
	// sumR fell to 1.849 G (floor is 6.5 G), and Q_stop dropped BELOW
	// Q_current in 1.7% of epochs -- so the predictor believed the queue was
	// emptying while it actually held 1.13 MB, and RED never tripped.
	// Use the batch high-water mark so the floor reflects the flows the drain
	// would have to starve.
	if (activeSenders > runtime.qcPeakActiveSenders)
		runtime.qcPeakActiveSenders = activeSenders;
	const long double floorBps =
		(long double)runtime.qcPeakActiveSenders * (long double)minRateBps +
		(long double)minRateBps;
	long double drainMax = C > floorBps ? C - floorBps : 0.0L;
	if (drainMax < 0.0L)
		drainMax = 0.0L;

	const long double deadband =
		(long double)s_cbapConfig.qcOnWirePacketBytes * 8.0L / hGuard;

	// --- confirmation: pending -> effective, then it PERSISTS ------------
	if (runtime.qcPendingGeneration != 0 && nowNs >= runtime.qcPendingEtaNs) {
		runtime.qcBoostEffectiveBps = runtime.qcBoostCommandedBps;
		runtime.qcDrainTargetBps = runtime.qcDrainCommandedBps;
		runtime.qcBoostCommandedBps = 0;
		runtime.qcDrainCommandedBps = 0;
		runtime.qcPendingGeneration = 0;
		runtime.qcPendingEtaNs = 0;
	}

	// --- Q_stop: worst case over [now, now+H_guard], not the endpoint ----
	// Sampling only the endpoint hides an intra-window peak the queue then
	// drains back from.  Take the max over the segment boundaries.
	const long double uEff = (long double)runtime.qcBoostEffectiveBps -
		(long double)runtime.qcDrainTargetBps;
	long double tau = 0.0L;
	long double uPend = uEff;
	if (runtime.qcPendingGeneration != 0 &&
			runtime.qcPendingEtaNs > nowNs) {
		tau = (long double)(runtime.qcPendingEtaNs - nowNs) / 1e9L;
		if (tau > hGuard)
			tau = hGuard;
		uPend = (long double)runtime.qcBoostCommandedBps -
			(long double)runtime.qcDrainCommandedBps;
	} else {
		tau = hGuard;
	}
	const long double qAtTau = (long double)queueBytes +
		(long double)pendingExcessBytes + uEff * tau / 8.0L;
	const long double qAtEnd = qAtTau + uPend * (hGuard - tau) / 8.0L;
	long double qStop = (long double)queueBytes +
		(long double)pendingExcessBytes;
	if (qAtTau > qStop)
		qStop = qAtTau;
	if (qAtEnd > qStop)
		qStop = qAtEnd;
	// Invariant Q_stop >= Q_current: violating it means the predictor believes
	// the queue drains faster than any legal drain allows.
	if (qStop < (long double)queueBytes)
		qStop = (long double)queueBytes;

	const long double qSafe = qStop + mSafe;
	runtime.qcQStopBytes = (uint64_t)qStop;
	runtime.qcQSafeBytes = (uint64_t)qSafe;
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

	// RED preempts everything, including a pending transition.
	if (zone == 3) {
		runtime.qcBoostCommandedBps = 0;
		runtime.qcDrainCommandedBps = (uint64_t)drainMax;
		runtime.qcBoostEffectiveBps = 0;
		runtime.qcDrainTargetBps = (uint64_t)drainMax;
		runtime.qcPendingGeneration = 0;
		runtime.qcPendingEtaNs = 0;
		return;
	}

	// --- desired absolute target ----------------------------------------
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

	const long double curU = (long double)runtime.qcBoostEffectiveBps -
		(long double)runtime.qcDrainTargetBps;
	if (runtime.qcPendingGeneration != 0) {
		const long double pend =
			(long double)runtime.qcBoostCommandedBps -
			(long double)runtime.qcDrainCommandedBps;
		// Only a safer (lower) target may preempt a pending transition.
		if (desired < pend - deadband) {
			runtime.qcGenerationCounter++;
			runtime.qcBoostCommandedBps =
				(uint64_t)(desired > 0.0L ? desired : 0.0L);
			runtime.qcDrainCommandedBps =
				(uint64_t)(desired < 0.0L ? -desired : 0.0L);
			runtime.qcPendingGeneration = runtime.qcGenerationCounter;
			runtime.qcPendingEtaNs = nowNs + (uint64_t)(hGuard * 1e9L);
		}
		return;
	}
	long double delta = desired - curU;
	if (delta < 0.0L)
		delta = -delta;
	if (delta < deadband)
		return;                      // the working band IS the deadband
	runtime.qcGenerationCounter++;
	runtime.qcBoostCommandedBps = (uint64_t)(desired > 0.0L ? desired : 0.0L);
	runtime.qcDrainCommandedBps = (uint64_t)(desired < 0.0L ? -desired : 0.0L);
	runtime.qcPendingGeneration = runtime.qcGenerationCounter;
	runtime.qcPendingEtaNs = nowNs + (uint64_t)(hGuard * 1e9L);
}

'''

c = c[:start] + new + c[nxt:]
io.open(pc, 'w', encoding='utf-8', errors='surrogateescape').write(c)
print("working-band controller written; zones=%d drainMax refs=%d"
      % (c.count('zone = 3'), c.count('drainMax')))
