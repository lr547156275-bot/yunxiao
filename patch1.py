import io
p='/work/simulation/scratch/third.cc'
src=io.open(p,encoding='utf-8',errors='surrogateescape').read()

a1="string cbap_port_summary_file, cbap_admission_file;"
assert src.count(a1)==1, ("a1",src.count(a1))
src=src.replace(a1, a1+"""
// --- PFC / actuation audit trace (measurement only; no control effect) ------
// Records the EXACT inputs of the real PFC pause predicate
// (SwitchMmu::CheckShouldPause) alongside CBAP's egress queue_bytes, so the two
// can be compared without assuming they are the same quantity.  They are not:
// PFC is evaluated per INGRESS port on ingress_bytes[], while CBAP samples the
// EGRESS BEgressQueue of the bottleneck port.
string cbap_pfc_audit_file;
static FILE *cbap_pfc_audit_csv = NULL;
""")

a2="RdmaHw::CbapPortSnapshot ReadCbapPort(uint32_t linkId){"
assert src.count(a2)==1, ("a2",src.count(a2))
sampler=r'''// Sample every input of the real PFC predicate on the bottleneck switch.
// Read-only: uses the same accessors CheckShouldPause uses, changes nothing.
static void SampleCbapPfcAudit(uint32_t linkId, uint64_t egressQueueBytes){
	if (!cbap_pfc_audit_csv)
		return;
	map<uint32_t, RdmaHw::BopMultilinkLink>::const_iterator definition =
		cbap_link_by_id.find(linkId);
	if (definition == cbap_link_by_id.end())
		return;
	Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(
		n.Get(definition->second.nodeId));
	if (!sw || !sw->m_mmu)
		return;
	Ptr<SwitchMmu> mmu = sw->m_mmu;
	const uint32_t q = cbap_priority;
	const uint32_t nDev = sw->GetNDevices();
	// The PFC predicate is per INGRESS port.  Report the worst (closest to
	// pausing) ingress port, the aggregate shared-pool state, and the egress
	// port CBAP controls -- separately, never summed into one "queue".
	uint32_t worstPort = 0, worstOcc = 0, worstThresh = 0, worstHdrm = 0;
	long long worstSlack = 0;
	bool first = true, anyPaused = false;
	uint32_t sumIngress = 0;
	for (uint32_t p = 1; p < nDev; ++p){
		uint32_t occ = mmu->GetSharedUsed(p, q);
		uint32_t th = mmu->GetPfcThreshold(p);
		uint32_t hd = mmu->hdrm_bytes[p][q];
		sumIngress += mmu->ingress_bytes[p][q];
		if (mmu->IsPaused(p, q))
			anyPaused = true;
		long long slack = (long long)th - (long long)occ;
		if (first || slack < worstSlack){
			worstSlack = slack; worstPort = p; worstOcc = occ;
			worstThresh = th; worstHdrm = hd;
			first = false;
		}
	}
	// pfc_guard_state mirrors CheckShouldPause exactly:
	//   hdrm_bytes[port][q] > 0 || GetSharedUsed(port,q) >= GetPfcThreshold(port)
	const char *state = "SAFE";
	if (anyPaused)
		state = "PAUSED";
	else if (worstHdrm > 0 || worstOcc >= worstThresh)
		state = "TRIGGER";
	else if (worstThresh > 0 && worstSlack < (long long)(worstThresh / 8))
		state = "NEAR";
	uint32_t egressPortOcc = definition->second.ifIndex < nDev ?
		mmu->egress_bytes[definition->second.ifIndex][q] : 0;
	fprintf(cbap_pfc_audit_csv,
		"%lu,%u,%lu,%u,%u,%u,%u,%lld,%u,%u,%u,%u,%u,%s\n",
		(unsigned long)Simulator::Now().GetTimeStep(), linkId,
		(unsigned long)egressQueueBytes, egressPortOcc,
		worstPort, worstOcc, worstThresh, worstSlack, worstHdrm,
		mmu->shared_used_bytes, mmu->total_hdrm, mmu->total_rsrv,
		sumIngress, state);
}

'''
src=src.replace(a2, sampler+a2)

a3="""	snapshot.queueBytes =
		sw->GetEgressQueueBytes(definition->second.ifIndex);"""
assert src.count(a3)==1, ("a3",src.count(a3))
src=src.replace(a3, a3+"""
	SampleCbapPfcAudit(linkId, snapshot.queueBytes);""")

io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(src)
print("OK: globals + sampler + call site patched")
