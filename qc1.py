import io
ph='/work/simulation/src/point-to-point/model/rdma-hw.h'
h=io.open(ph,encoding='utf-8',errors='surrogateescape').read()
assert h.count("queueControllerEnable")==0, "already patched"

# --- config fields: NEW names, no reuse of the EXPERIMENTAL credit fields ----
a='''		bool delayCreditEnable;'''
assert h.count(a)==1
h=h.replace(a,'''		// --- queue-bounded boost/drain controller (method D) ----------------
		// Deliberately SEPARATE fields from the EXPERIMENTAL/NOT VALID
		// delay-credit block below.  Nothing here reuses delayCreditEnable,
		// maxOversubRatio, creditMaxDrainRatio or the queueDelay* fields; that
		// path stays dead.  All default to off/zero.
		bool queueControllerEnable;   // CBAP_QUEUE_CONTROLLER_ENABLE, default 0
		double qcSoftFraction;        // soft = this * app_hard_delay
		double qcMaxBoostRatio;       // boost_target <= this * C
		double qcHGuardS;             // H_guard, seconds (measured 175 us)
		double qcAppHardDelayS;       // message_size * 8 / C
		uint64_t qcOnWirePacketBytes; // for the packetization margin
''' + a)

# --- per-link controller state ---------------------------------------------
b='''		CbapQueuePhase queuePhase;'''
assert h.count(b)==1
h=h.replace(b,'''		// Queue-controller state, per link.  boost_effective PERSISTS until a
		// new absolute target replaces it: it does not expire with H_guard and
		// never reverts to C.
		uint64_t qcBoostEffectiveBps;
		uint64_t qcBoostCommandedBps;   // the single pending absolute target
		uint64_t qcPendingGeneration;   // 0 = none pending
		uint64_t qcDrainTargetBps;
		uint64_t qcGenerationCounter;
		uint64_t qcCommandTimeNs;       // when the pending target was issued
		uint32_t qcZone;                // 0 GREEN, 1 YELLOW, 2 RED
		uint64_t qcGuardExceeded;       // observed H_eff > H_guard, must stay 0
''' + b)

c='''			  queuePhase(CBAP_QPHASE_SYNC_BURST), syncBurstObserved(false),'''
assert h.count(c)==1
h=h.replace(c,'''			  qcBoostEffectiveBps(0), qcBoostCommandedBps(0),
			  qcPendingGeneration(0), qcDrainTargetBps(0),
			  qcGenerationCounter(0), qcCommandTimeNs(0), qcZone(0),
			  qcGuardExceeded(0),
			  queuePhase(CBAP_QPHASE_SYNC_BURST), syncBurstObserved(false),''')

d='''			  delayCreditEnable(false), queueDelayTargetS(0.0),'''
assert h.count(d)==1
h=h.replace(d,'''			  queueControllerEnable(false), qcSoftFraction(0.0),
			  qcMaxBoostRatio(0.0), qcHGuardS(0.0), qcAppHardDelayS(0.0),
			  qcOnWirePacketBytes(0),
			  delayCreditEnable(false), queueDelayTargetS(0.0),''')

# --- the decision function declaration ------------------------------------
e='	static void ConfigureCbap('
assert h.count(e)==1
h=h.replace(e,'''	// One control epoch of the queue-bounded controller.  Provably inert when
	// queueControllerEnable is false (early return before any state change).
	static void QueueControllerEpoch(CbapLinkRuntime &runtime,
		uint64_t nowNs, uint64_t queueBytes, uint64_t rEffectiveBps,
		uint64_t pendingExcessBytes, uint32_t activeSenders,
		bool pfcSafe, uint64_t ledgerCountedBurstBytes);
''' + e)
io.open(ph,'w',encoding='utf-8',errors='surrogateescape').write(h)
print("rdma-hw.h patched: cfg=%d state=%d decl=%d"
      % (h.count("queueControllerEnable"), h.count("qcBoostEffectiveBps"),
         h.count("QueueControllerEpoch")))
