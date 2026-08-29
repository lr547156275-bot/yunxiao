import io

# --- snapshot: expose the new wire-domain and epoch fields -----------------
ph = '/work/simulation/src/point-to-point/model/rdma-hw.h'
h = io.open(ph, encoding='utf-8', errors='surrogateescape').read()
if h.count('q0Bytes') == 0:
    a = '\t\tuint32_t protectedCount;\n\t};'
    assert h.count(a) == 1, ('snap', h.count(a))
    h = h.replace(a,
'''		uint32_t protectedCount;
		// Same-epoch accounting: q0 is THE sample used for control and for
		// this trace row. q_next belongs to the next epoch and must not be
		// paired with this row's Q_stop.
		uint64_t q0Bytes, epochId, prefixMaxIndex;
		uint64_t floorWireBps, floorPayloadBps, drainMaxWireBps;
		uint64_t arrivalSafeWireBps, senderEffectiveWireBps;
		uint64_t duplicateQpCount;
		bool ownsRates, exitRecoveryPending, inRed;
	};''')
    io.open(ph, 'w', encoding='utf-8', errors='surrogateescape').write(h)

pc = '/work/simulation/src/point-to-point/model/rdma-hw.cc'
c = io.open(pc, encoding='utf-8', errors='surrogateescape').read()
old = '''	out->protectedCount =
		(uint32_t)it->second.qcProtectedQps.size();
	return true;'''
assert c.count(old) == 1, ('acc', c.count(old))
c = c.replace(old,
'''	out->protectedCount =
		(uint32_t)it->second.qcProtectedQps.size();
	out->q0Bytes = it->second.qcQ0Bytes;
	out->epochId = it->second.qcEpochId;
	out->prefixMaxIndex = it->second.qcPrefixMaxIndex;
	out->floorWireBps = it->second.qcFloorWireBps;
	out->floorPayloadBps = it->second.qcFloorPayloadBps;
	out->drainMaxWireBps = it->second.qcDrainMaxWireBps;
	out->arrivalSafeWireBps = it->second.qcArrivalSafeWireBps;
	out->senderEffectiveWireBps = it->second.qcSenderEffectiveWireBps;
	out->duplicateQpCount = it->second.qcDuplicateQpCount;
	out->ownsRates = it->second.qcOwnsRates;
	out->exitRecoveryPending = it->second.qcExitRecoveryPending;
	out->inRed = it->second.qcInRed;
	return true;''')
io.open(pc, 'w', encoding='utf-8', errors='surrogateescape').write(c)

# --- trace: q0 from the controller, plus the separated rate columns --------
p = '/work/simulation/scratch/third.cc'
s = io.open(p, encoding='utf-8', errors='surrogateescape').read()
st = s.index('static void SampleCbapQcTrace')
en = s.index('\n}\n', st) + 3
new = r'''static void SampleCbapQcTrace(uint32_t linkId, uint64_t queueBytes,
		uint64_t capacityBps){
	if (!cbap_qc_trace_csv)
		return;
	RdmaHw::CbapQcSnapshot qc;
	if (!RdmaHw::GetCbapQcStateForAudit(linkId, &qc))
		return;
	const char *zone = qc.zone == 3 ? "RED" :
		(qc.zone == 2 ? "YELLOW-DRAIN" :
		 (qc.zone == 1 ? "YELLOW-HOLD" : "GREEN"));
	const double sumR = (double)capacityBps + (double)qc.boostEffectiveBps -
		(double)qc.drainTargetBps;
	// q0 is the controller's OWN epoch sample; queueBytes read here is the
	// NEXT sample and is reported separately as q_next. Pairing this row's
	// Q_stop with q_next is what produced 3968 phantom "Q_stop < Q_current".
	fprintf(cbap_qc_trace_csv,
		"%lu,%u,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%.0f,%s,%lu,%lu,%lu,%lu,%lu,"
		"%lu,%lu,%lu,%lu,%u,%u,%u\n",
		(unsigned long)Simulator::Now().GetTimeStep(), linkId,
		(unsigned long)qc.epochId,
		(unsigned long)qc.q0Bytes,
		(unsigned long)queueBytes,
		(unsigned long)qc.qStopBytes,
		(unsigned long)qc.qSafeBytes,
		(unsigned long)qc.boostCommandedBps,
		(unsigned long)qc.boostEffectiveBps,
		(unsigned long)qc.drainTargetBps,
		sumR, zone,
		(unsigned long)qc.pendingGeneration,
		(unsigned long)qc.floorWireBps,
		(unsigned long)qc.floorPayloadBps,
		(unsigned long)qc.drainMaxWireBps,
		(unsigned long)qc.arrivalSafeWireBps,
		(unsigned long)qc.senderEffectiveWireBps,
		(unsigned long)qc.duplicateQpCount,
		(unsigned long)qc.invariantViolations,
		(unsigned long)qc.prefixMaxIndex,
		qc.protectedCount,
		qc.ownsRates ? 1u : 0u,
		qc.exitRecoveryPending ? 1u : 0u);
}
'''
s = s[:st] + new + s[en:]

oldh = [l for l in s.split('\n') if 'time_ns,link_id,q_current,q_stop' in l]
assert len(oldh) == 1, ('hdr lines', len(oldh))
i = s.index(oldh[0])
j = s.index('\\n");', i) + 5
s = s[:i] + ('\t\t\t\t"time_ns,link_id,epoch_id,q0,q_next,q_stop,q_safe,"\n'
             '\t\t\t\t"boost_commanded,boost_effective,drain,sumR_effective,"\n'
             '\t\t\t\t"zone,pending_generation,floor_wire_bps,'
             'floor_payload_bps,"\n'
             '\t\t\t\t"drain_max_wire_bps,arrival_safe_wire_bps,"\n'
             '\t\t\t\t"sender_effective_wire_bps,duplicate_qp_count,"\n'
             '\t\t\t\t"invariant_violations,prefix_max_index,protected_count,"\n'
             '\t\t\t\t"owns_rates,exit_recovery_pending\\n");') + s[j:]
io.open(p, 'w', encoding='utf-8', errors='surrogateescape').write(s)
print("trace: same-epoch q0 + q_next separated; 24 columns")
