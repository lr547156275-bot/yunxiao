import io

# 1) M_safe config key in third.cc
p = '/work/simulation/scratch/third.cc'
s = io.open(p, encoding='utf-8', errors='surrogateescape').read()
if s.count("CBAP_QC_SAFETY_MARGIN_BYTES") == 0:
    a = '\t\t\telse if(key.compare("CBAP_QC_SOFT_FRACTION")==0)\n' \
        '\t\t\t\tconf>>cbap_qc_soft_fraction;'
    assert s.count(a) == 1, ('key anchor', s.count(a))
    s = s.replace(a, a + '\n'
                  '\t\t\telse if(key.compare("CBAP_QC_SAFETY_MARGIN_BYTES")==0)\n'
                  '\t\t\t\tconf>>cbap_qc_safety_margin_bytes;')
    b = 'double cbap_qc_soft_fraction = 0.5;      ' \
        '// preflight value, not a paper param'
    assert s.count(b) == 1, ('global anchor', s.count(b))
    s = s.replace(b, b + '\n'
                  '// M_safe: measured prediction uncertainty + uncovered packet\n'
                  '// granularity. Set from the measured residual, not guessed.\n'
                  'uint64_t cbap_qc_safety_margin_bytes = 0;')
    c = '\tconfig.qcOnWirePacketBytes = cbap_max_wire_packet_bytes;'
    assert s.count(c) == 1, ('push anchor', s.count(c))
    s = s.replace(c, c + '\n'
                  '\tconfig.qcSafetyMarginBytes = cbap_qc_safety_margin_bytes;')
    io.open(p, 'w', encoding='utf-8', errors='surrogateescape').write(s)

# 2) the call site must pass a real pending_excess_bytes, never 0.
pc = '/work/simulation/src/point-to-point/model/rdma-hw.cc'
c2 = io.open(pc, encoding='utf-8', errors='surrogateescape').read()
old = '''		QueueControllerEpoch(runtime, record.deliveryTimeNs,
			record.queueBytes, rEffective, 0, nActive, pfcSafe, 0,
			minRateBps);'''
if c2.count(old) == 1:
    c2 = c2.replace(old, '''		// pending_excess_bytes: bytes already committed by an unconfirmed
		// command but not yet visible in queueBytes.  Passing 0 here (as an
		// earlier version did) removes the one term that accounts for the
		// controller's own in-flight effect.
		uint64_t pendingExcess = 0;
		if (runtime.qcPendingGeneration != 0 &&
				runtime.qcPendingEtaNs > record.deliveryTimeNs) {
			const uint64_t elapsed = record.deliveryTimeNs >
				runtime.qcCommandTimeNs ?
				record.deliveryTimeNs - runtime.qcCommandTimeNs : 0;
			const long double excess =
				(long double)runtime.qcBoostCommandedBps -
				(long double)runtime.qcDrainCommandedBps;
			if (excess > 0.0L)
				pendingExcess = (uint64_t)(excess *
					(long double)elapsed / 1e9L / 8.0L);
		}
		QueueControllerEpoch(runtime, record.deliveryTimeNs,
			record.queueBytes, rEffective, pendingExcess, nActive, pfcSafe, 0,
			minRateBps);''')
    io.open(pc, 'w', encoding='utf-8', errors='surrogateescape').write(c2)
    print("call site: pendingExcess now computed, not 0")
else:
    print("call site pattern not found (count=%d) -- check manually"
          % c2.count(old))
print("M_safe key present: %d" % s.count('"CBAP_QC_SAFETY_MARGIN_BYTES"'))
