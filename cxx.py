import io
pc='/work/simulation/src/point-to-point/model/rdma-hw.cc'
c=io.open(pc,encoding='utf-8',errors='surrogateescape').read()

# Replace the whole decision body with the signed-control version, so the C++
# matches controller_ref.py (31/31 unit, 17/17 replay).
start=c.index('void RdmaHw::QueueControllerEpoch(CbapLinkRuntime &runtime,')
end=c.index('uint64_t RdmaHw::ComputeDelayCreditBudget(CbapLinkRuntime &runtime,')
new = r'''void RdmaHw::QueueControllerEpoch(CbapLinkRuntime &runtime, uint64_t nowNs,
		uint64_t queueBytes, uint64_t rEffectiveBps,
		uint64_t pendingExcessBytes, uint32_t activeSenders, bool pfcSafe,
		uint64_t ledgerCountedBurstBytes, uint64_t minRateBps)
{
	// Gate 1: provably inert when disabled -- returns before touching state.
	if (!s_cbapConfig.queueControllerEnable)
		return;
	(void)rEffectiveBps;   // effective rate enters via the stored boost/drain
	const long double C = (long double)runtime.config.capacityBps;
	if (C <= 0.0L || s_cbapConfig.qcHGuardS <= 0.0 || minRateBps == 0)
		return;

	const long double hGuard = (long double)s_cbapConfig.qcHGuardS;
	const long double hardBytes =
		(long double)s_cbapConfig.qcAppHardDelayS * C / 8.0L;
	const long double softBytes =
		(long double)s_cbapConfig.qcSoftFraction * hardBytes;
	const long double maxBoost =
		(long double)s_cbapConfig.qcMaxBoostRatio * C;
	// MAX_DRAIN comes from the existing floor, not a new parameter.
	const long double floorBps =
		(long double)(activeSenders ? activeSenders : 1) *
		(long double)minRateBps + (long double)minRateBps;
	const long double maxDrain = C > floorBps ? C - floorBps : 0.0L;
	// Preemption / no-op deadband: per-flow actuation quantum, one on-wire
	// packet per guard window.  Without it the continuous law refreshes the
	// pending slot every epoch and the actuation ETA is pushed back forever.
	const long double deadband =
		(long double)s_cbapConfig.qcOnWirePacketBytes * 8.0L / hGuard;
	// Rearm line: packetization burst + one actuation step below soft.
	const long double rearmBytes = softBytes -
		((long double)activeSenders *
			(long double)s_cbapConfig.qcOnWirePacketBytes +
		 maxBoost * hGuard / 8.0L);

	const long double curU = (long double)runtime.qcBoostEffectiveBps -
		(long double)runtime.qcDrainTargetBps;

	// --- Q_stop: pending integrated by its ETA, NOT max(eff, pending).
	long double qStop;
	if (runtime.qcPendingGeneration != 0 && runtime.qcPendingEtaNs > nowNs) {
		long double tau =
			(long double)(runtime.qcPendingEtaNs - nowNs) / 1e9L;
		if (tau > hGuard)
			tau = hGuard;
		const long double uPend =
			(long double)runtime.qcBoostCommandedBps -
			(long double)runtime.qcDrainCommandedBps;
		qStop = (long double)queueBytes + (long double)pendingExcessBytes +
			curU * tau / 8.0L + uPend * (hGuard - tau) / 8.0L;
	} else {
		qStop = (long double)queueBytes + (long double)pendingExcessBytes +
			curU * hGuard / 8.0L;
	}
	if (qStop < 0.0L)
		qStop = 0.0L;

	long double margin = (long double)activeSenders *
		(long double)s_cbapConfig.qcOnWirePacketBytes -
		(long double)ledgerCountedBurstBytes;
	if (margin < 0.0L)
		margin = 0.0L;
	const long double qSafe = qStop + margin;

	// RED on Q_safe, so it fires BEFORE the queue actually crosses hard.
	uint32_t zone;
	if (qSafe >= hardBytes || !pfcSafe)
		zone = 2;
	else if (qStop >= softBytes)
		zone = 1;
	else
		zone = 0;
	runtime.qcZone = zone;
	runtime.qcActiveSenders = activeSenders;

	if (runtime.qcRearmRequired && qStop < rearmBytes)
		runtime.qcRearmRequired = false;

	if (zone == 2) {
		// Preempts everything, including a pending descent.
		runtime.qcBoostCommandedBps = 0;
		runtime.qcDrainCommandedBps = 0;
		runtime.qcPendingGeneration = 0;
		runtime.qcPendingEtaNs = 0;
		runtime.qcDescending = false;
		runtime.qcBoostEffectiveBps = 0;
		runtime.qcDrainTargetBps = (uint64_t)maxDrain;
		return;
	}

	// --- continuous signed law: u = MAX_BOOST*(1-p) - MAX_DRAIN*p
	const long double span = hardBytes - softBytes;
	long double p = span > 0.0L ? (qStop - softBytes) / span : 0.0L;
	if (p < 0.0L)
		p = 0.0L;
	if (p > 1.0L)
		p = 1.0L;
	long double desired = maxBoost * (1.0L - p) - maxDrain * p;

	// Direction hysteresis: hold the current target, never force it to zero --
	// zeroing creates a dQ/dt == 0 fixed point wherever the descent landed.
	if ((runtime.qcDescending || runtime.qcRearmRequired) && desired > curU)
		desired = curU;

	if (runtime.qcPendingGeneration != 0) {
		const long double uPend =
			(long double)runtime.qcBoostCommandedBps -
			(long double)runtime.qcDrainCommandedBps;
		// Only a MEANINGFULLY lower target may preempt.
		if (desired < uPend - deadband) {
			runtime.qcGenerationCounter++;
			runtime.qcBoostCommandedBps = (uint64_t)std::max(0.0L, desired);
			runtime.qcDrainCommandedBps = (uint64_t)std::max(0.0L, -desired);
			runtime.qcPendingGeneration = runtime.qcGenerationCounter;
			runtime.qcPendingEtaNs = nowNs +
				(uint64_t)(hGuard * 1e9L);
			runtime.qcDescending = desired < curU - deadband;
		}
		return;
	}

	long double delta = desired - curU;
	if (delta < 0.0L)
		delta = -delta;
	if (delta < deadband)
		return;                     // no-op: recompute is not recommand
	runtime.qcGenerationCounter++;
	runtime.qcBoostCommandedBps = (uint64_t)std::max(0.0L, desired);
	runtime.qcDrainCommandedBps = (uint64_t)std::max(0.0L, -desired);
	runtime.qcPendingGeneration = runtime.qcGenerationCounter;
	runtime.qcPendingEtaNs = nowNs + (uint64_t)(hGuard * 1e9L);
	runtime.qcDescending = desired < curU - deadband;
}

'''
c = c[:start] + new + c[end:]
io.open(pc,'w',encoding='utf-8',errors='surrogateescape').write(c)
print("C++ decision function replaced with the signed law")
