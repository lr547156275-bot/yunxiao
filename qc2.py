import io
pc='/work/simulation/src/point-to-point/model/rdma-hw.cc'
c=io.open(pc,encoding='utf-8',errors='surrogateescape').read()
assert c.count("RdmaHw::QueueControllerEpoch")==0, "already patched"

anchor='uint64_t RdmaHw::ComputeDelayCreditBudget(CbapLinkRuntime &runtime,'
assert c.count(anchor)==1
fn = r'''// Queue-bounded boost/drain controller, one control epoch.  Method D:
// boost is a PERSISTENT ABSOLUTE TARGET with a single pending transition.
//
// Mirrors controller_state_machine_test.py (31/31).  A disagreement between the
// two is itself a finding.
//
//   sumR_target = C + boost_target - drain_target,   both >= 0, never both > 0
//
//   Q_stop = max(0, Q + max(excess_effective, excess_pending) * H_guard / 8)
//            -> drives the SOFT/pressure decision
//   Q_safe = Q_stop + packetization_margin   (applied once, never accumulated)
//            -> hard-bound and PFC safety only
//
// boost_effective persists until a new absolute target replaces it: it does NOT
// expire with H_guard and never reverts to C.  "One pending generation" forbids
// overlapping UNCONFIRMED commands only, not the holding of an effective boost.
//
// This function shares NOTHING with the EXPERIMENTAL/NOT VALID delay-credit
// path below: separate config fields, separate state, separate call site.
void RdmaHw::QueueControllerEpoch(CbapLinkRuntime &runtime, uint64_t nowNs,
		uint64_t queueBytes, uint64_t rEffectiveBps,
		uint64_t pendingExcessBytes, uint32_t activeSenders, bool pfcSafe,
		uint64_t ledgerCountedBurstBytes)
{
	// Gate 1: provably inert when disabled -- returns before touching state.
	if (!s_cbapConfig.queueControllerEnable)
		return;
	const long double C = (long double)runtime.config.capacityBps;
	if (C <= 0.0L || s_cbapConfig.qcHGuardS <= 0.0)
		return;

	const long double hardBytes =
		(long double)s_cbapConfig.qcAppHardDelayS * C / 8.0L;
	const long double softBytes =
		(long double)s_cbapConfig.qcSoftFraction * hardBytes;
	const long double maxBoost =
		(long double)s_cbapConfig.qcMaxBoostRatio * C;
	const long double hGuard = (long double)s_cbapConfig.qcHGuardS;

	// --- Q_stop: net backlog until the earliest brake could take effect.
	// Uses the EFFECTIVE rate and the single PENDING target -- never a desired
	// rate that has not been commanded.  The worse of the two is taken so the
	// brake is never under-estimated.
	long double excessEff = (long double)runtime.qcBoostEffectiveBps -
		(long double)runtime.qcDrainTargetBps;
	long double excess = excessEff;
	if (runtime.qcPendingGeneration != 0) {
		long double excessPending =
			(long double)runtime.qcBoostCommandedBps -
			(long double)runtime.qcDrainTargetBps;
		if (excessPending > excess)
			excess = excessPending;
	}
	long double qStop = (long double)queueBytes +
		(long double)pendingExcessBytes + excess * hGuard / 8.0L;
	if (qStop < 0.0L)
		qStop = 0.0L;

	// --- Q_safe: plus the packetization margin, de-duplicated against the
	// pending ledger and applied ONCE (never accumulated across epochs).
	long double margin = (long double)activeSenders *
		(long double)s_cbapConfig.qcOnWirePacketBytes;
	margin -= (long double)ledgerCountedBurstBytes;
	if (margin < 0.0L)
		margin = 0.0L;
	const long double qSafe = qStop + margin;

	// --- zone.  SOFT uses Q_stop; Q_safe only participates in the hard check.
	uint32_t zone;
	if (qSafe >= hardBytes || qStop >= hardBytes)
		zone = 2;                       // RED
	else if (qStop >= softBytes)
		zone = 1;                       // YELLOW
	else
		zone = 0;                       // GREEN
	runtime.qcZone = zone;

	// --- desired absolute target for this zone.
	long double desired = 0.0L;
	if (zone == 0 && pfcSafe) {
		desired = maxBoost;
	} else if (zone == 1 && pfcSafe) {
		const long double span = hardBytes - softBytes;
		long double remaining = span > 0.0L ?
			(hardBytes - qStop) / span : 0.0L;
		if (remaining < 0.0L)
			remaining = 0.0L;
		desired = maxBoost * remaining * remaining;   // non-linear decay
	}

	runtime.qcDrainTargetBps = 0;
	if (zone == 2) {
		// RED preempts everything: clear boost, clear any pending command,
		// and drain so the aggregate target falls below C.
		runtime.qcBoostEffectiveBps = 0;
		runtime.qcBoostCommandedBps = 0;
		runtime.qcPendingGeneration = 0;
		long double over = qStop - softBytes;
		if (over < 0.0L)
			over = 0.0L;
		long double drain = over * 8.0L / hGuard;
		// Never drain below the sum of all active minimum rates.
		const long double floorBps =
			(long double)(activeSenders ? activeSenders : 1) *
			(long double)m_minRateStaticBps + (long double)m_minRateStaticBps;
		const long double maxDrain = C > floorBps ? C - floorBps : 0.0L;
		if (drain > maxDrain)
			drain = maxDrain;
		if (drain < 1.0L)
			drain = 1.0L;
		runtime.qcDrainTargetBps = (uint64_t)drain;
	} else if (!pfcSafe) {
		// PFC veto: an independent safety veto.  Forbids positive boost only;
		// it never blocks drain (handled in the RED branch above).
		runtime.qcBoostEffectiveBps = 0;
		runtime.qcBoostCommandedBps = 0;
		runtime.qcPendingGeneration = 0;
	} else if (runtime.qcPendingGeneration != 0) {
		// A pending transition exists: update the prediction only.  Issuing a
		// second unconfirmed command is exactly what must not happen.
		// Timeout is a safety valve, not an expiry of the effective boost.
		if (nowNs > runtime.qcCommandTimeNs &&
				(long double)(nowNs - runtime.qcCommandTimeNs) >
					hGuard * 1e9L * 2.0L) {
			runtime.qcGuardExceeded++;
			runtime.qcPendingGeneration = 0;
			runtime.qcBoostCommandedBps = 0;
		}
	} else {
		// Nothing pending.  Recomputing every epoch is NOT commanding every
		// epoch: only a CHANGE of the absolute target issues a command.
		long double delta = desired -
			(long double)runtime.qcBoostEffectiveBps;
		if (delta < 0.0L)
			delta = -delta;
		if (delta >= 1.0L) {
			runtime.qcGenerationCounter++;
			runtime.qcBoostCommandedBps = (uint64_t)desired;
			runtime.qcPendingGeneration = runtime.qcGenerationCounter;
			runtime.qcCommandTimeNs = nowNs;
		}
	}
}

'''
c=c.replace(anchor, fn+anchor)
io.open(pc,'w',encoding='utf-8',errors='surrogateescape').write(c)
print("QueueControllerEpoch defined:", c.count("RdmaHw::QueueControllerEpoch"))
