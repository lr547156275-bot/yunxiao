import io
p='/work/simulation/scratch/third.cc'
src=io.open(p,encoding='utf-8',errors='surrogateescape').read()
NL=chr(92)+'n'

# Diagnostic: log EVERY armed dequeue with both ids, so a mismatch is visible
# rather than silently filtered.  Capped to avoid a firehose.
old='''	if (qp->crfm.flowId != cbap_pending_effect_flow)
		return;
	if (cbap_last_sender_effect_ns != 0)
		return;                       // only the FIRST departure counts'''
assert src.count(old)==1
src=src.replace(old,'''	if (cbap_last_sender_effect_ns != 0)
		return;                       // only the FIRST departure counts
	if (qp->crfm.flowId != cbap_pending_effect_flow){
		// Diagnostic, bounded: record the id mismatch instead of filtering it
		// away, so "no stage-2 rows" cannot be mistaken for "no departures".
		static uint32_t mismatchLogged = 0;
		if (mismatchLogged < 20){
			mismatchLogged++;
			fprintf(cbap_actuation_csv,
				"%lu,%lu,0,0,id_mismatch_qp_crfm_%lu,0,0''' + NL + '''",
				(unsigned long)Simulator::Now().GetTimeStep(),
				(unsigned long)cbap_pending_effect_flow,
				(unsigned long)qp->crfm.flowId);
		}
		return;
	}''')
io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(src)
print("diagnostic added:", src.count("id_mismatch_qp_crfm"))
