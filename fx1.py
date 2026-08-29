import io

# Header: per-QP actuation ledger, ownership lifecycle, wire-domain fields.
ph = '/work/simulation/src/point-to-point/model/rdma-hw.h'
h = io.open(ph, encoding='utf-8', errors='surrogateescape').read()

if h.count('CbapQpLedger') == 0:
    anchor = '\tstruct CbapLinkRuntime {'
    assert h.count(anchor) == 1, ('anchor', h.count(anchor))
    h = h.replace(anchor,
'''	// Per-QP pending actuation ledger.  The controller previously used the
	// SENDER pacing sum as if it were the bottleneck ARRIVAL rate; measured
	// consequence was a 3.97 G gap (sender 6.6 G while the bottleneck still
	// received 10.57 G of old-rate packets), which is what drove the queue
	// 128,329 B past Q_abs.  Arrival must be predicted with a safe envelope
	// until a command can possibly have taken effect.
	struct CbapQpLedger {
		uint32_t generation;
		uint64_t commandTimeNs;
		uint64_t effectDeadlineNs;      // commandTimeNs + H_guard
		uint64_t oldWireBps;            // arrival rate before the command
		uint64_t commandedWireBps;      // absolute target, never a delta
		uint64_t senderEffectiveWireBps;
		uint64_t predictedArrivalWireBps;
		uint64_t minRatePayloadBps;
		uint64_t wirePacketBytes;
		uint64_t payloadPacketBytes;
		bool pendingUp;
		bool pendingDown;
		bool ownsRate;                  // controller_owns_rates for this QP
		bool exitRecoveryPending;
		CbapQpLedger()
			: generation(0), commandTimeNs(0), effectDeadlineNs(0),
			  oldWireBps(0), commandedWireBps(0),
			  senderEffectiveWireBps(0), predictedArrivalWireBps(0),
			  minRatePayloadBps(0), wirePacketBytes(0),
			  payloadPacketBytes(0), pendingUp(false), pendingDown(false),
			  ownsRate(false), exitRecoveryPending(false) {}
	};
''' + anchor)

    a2 = '\t\tuint64_t qcBackgroundFloorBps;'
    assert h.count(a2) == 1, ('bg field', h.count(a2))
    h = h.replace(a2,
'''		// REMOVED: qcBackgroundFloorBps.  It double-counted the background
		// flow, which is already a member of qcProtectedQps -- 65 members
		// plus one extra gave 6.600 G where 65 unique QPs give 6.500 G
		// payload.  The floor is now computed only from the unique set.
		std::map<uint32_t, CbapQpLedger> qcLedger;
		bool qcOwnsRates;
		bool qcExitRecoveryPending;
		uint64_t qcFloorWireBps;
		uint64_t qcFloorPayloadBps;
		uint64_t qcDrainMaxWireBps;
		uint64_t qcArrivalSafeWireBps;
		uint64_t qcSenderEffectiveWireBps;
		uint64_t qcServedWireBps;
		uint64_t qcQ0Bytes;             // the ONE queue sample for this epoch
		uint64_t qcEpochId;
		uint64_t qcDuplicateQpCount;
		uint64_t qcPrefixMaxIndex;''')

    a3 = '\t\t\t  qcBackgroundFloorBps(0),'
    assert h.count(a3) == 1, ('bg init', h.count(a3))
    h = h.replace(a3,
'''			  qcOwnsRates(false), qcExitRecoveryPending(false),
			  qcFloorWireBps(0), qcFloorPayloadBps(0),
			  qcDrainMaxWireBps(0), qcArrivalSafeWireBps(0),
			  qcSenderEffectiveWireBps(0), qcServedWireBps(0),
			  qcQ0Bytes(0), qcEpochId(0), qcDuplicateQpCount(0),
			  qcPrefixMaxIndex(0),''')
    io.open(ph, 'w', encoding='utf-8', errors='surrogateescape').write(h)

print("header: ledger=%d ownsRates=%d bgFloor_removed=%s"
      % (h.count('CbapQpLedger'), h.count('qcOwnsRates'),
         h.count('qcBackgroundFloorBps') == 1))
