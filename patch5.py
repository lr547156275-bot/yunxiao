import io
p='/work/simulation/scratch/third.cc'
src=io.open(p,encoding='utf-8',errors='surrogateescape').read()
NL=chr(92)+'n'

# Extend the sampler: emit one row per contributing ingress port.
anchor='''	uint32_t egressPortOcc = definition->second.ifIndex < nDev ?
		mmu->egress_bytes[definition->second.ifIndex][q] : 0;'''
assert src.count(anchor)==1
add='''	// Per-port detail for every ingress port that actually carries traffic
	// toward this egress.  "Contributing" is decided by observed rx bytes, not
	// assumed from the topology, so a port that never carries data cannot
	// depress the reported minimum slack.
	if (cbap_pfc_ports_csv){
		long double slackMinReal = 0;
		bool haveReal = false;
		for (uint32_t pt = 1; pt < nDev; ++pt){
			if (pt == definition->second.ifIndex)
				continue;
			uint64_t rx = sw->GetRxBytes(pt);
			if (rx == 0)
				continue;                 // not a contributor
			uint32_t occ = mmu->GetSharedUsed(pt, q);
			uint32_t th = mmu->GetPfcThreshold(pt);
			uint32_t hd = mmu->hdrm_bytes[pt][q];
			long long slack = (long long)th - (long long)occ;
			if (!haveReal || slack < slackMinReal){
				slackMinReal = slack; haveReal = true;
			}
			fprintf(cbap_pfc_ports_csv,
				"%lu,%u,%u,%u,%u,%u,%lld,%u,%u,%u,%lu''' + NL + '''",
				(unsigned long)Simulator::Now().GetTimeStep(), linkId, pt,
				mmu->ingress_bytes[pt][q], occ, th, slack, hd,
				mmu->IsPaused(pt, q) ? 1u : 0u,
				mmu->egress_bytes[pt][q], (unsigned long)rx);
		}
	}
'''
src=src.replace(anchor, add+anchor)
io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(src)
print("per-port block inserted:", src.count("not a contributor"))
