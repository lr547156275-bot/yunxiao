import io
NL=chr(92)+'n'

# --- rdma-hw.cc: expose the rate-command instant via a read-only hook -------
ph='/work/simulation/src/point-to-point/model/rdma-hw.h'
h=io.open(ph,encoding='utf-8',errors='surrogateescape').read()
assert h.count("s_cbapActuationHook")==0, "h already patched"
a='	static void ConfigureCbap('
assert h.count(a)==1
h=h.replace(a, '''	// Read-only actuation audit hook.  Called immediately after a migration
	// rate command is written, with (flowId, oldBps, newBps).  Null by default,
	// so no behaviour changes unless a scenario installs it.  Not used by any
	// control decision.
	static void (*s_cbapActuationHook)(uint32_t, uint64_t, uint64_t);
''' + a)
io.open(ph,'w',encoding='utf-8',errors='surrogateescape').write(h)

pc='/work/simulation/src/point-to-point/model/rdma-hw.cc'
c=io.open(pc,encoding='utf-8',errors='surrogateescape').read()
assert c.count("s_cbapActuationHook")==0, "cc already patched"
a2='std::set<uint32_t> RdmaHw::s_cbapSbaMigrationPlanned;'
assert c.count(a2)==1
c=c.replace(a2, 'void (*RdmaHw::s_cbapActuationHook)(uint32_t, uint64_t, uint64_t) = NULL;\n'+a2)

a3='''		if (currentRate != appliedRate)
			flow->second.hw->ChangeRate(qp, DataRate(appliedRate));'''
assert c.count(a3)==1
c=c.replace(a3, '''		if (currentRate != appliedRate) {
			flow->second.hw->ChangeRate(qp, DataRate(appliedRate));
			// rate_command_time: the instant the new pacing rate is installed.
			if (s_cbapActuationHook)
				s_cbapActuationHook(flow->first, currentRate, appliedRate);
		}''')
io.open(pc,'w',encoding='utf-8',errors='surrogateescape').write(c)
print("rdma-hw: hook declared=%d defined=%d called=%d"
      % (h.count("s_cbapActuationHook"), c.count("RdmaHw::s_cbapActuationHook"),
         c.count("s_cbapActuationHook(flow->first")))
