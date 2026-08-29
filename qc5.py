import io
p='/work/simulation/scratch/third.cc'
s=io.open(p,encoding='utf-8',errors='surrogateescape').read()
for k in ("CBAP_QUEUE_CONTROLLER_ENABLE","CBAP_QC_SOFT_FRACTION",
          "CBAP_QC_MAX_BOOST_RATIO","CBAP_QC_H_GUARD_US",
          "CBAP_QC_APP_HARD_DELAY_US","CBAP_QC_TRACE_FILE"):
    assert s.count(k)==0, ("collision",k,s.count(k))

a='string cbap_pfc_audit_file;'
assert s.count(a)==1
s=s.replace(a,'''// --- queue-bounded controller (method D).  All default OFF/zero. -----------
uint32_t cbap_queue_controller_enable = 0;
double cbap_qc_soft_fraction = 0.5;      // preflight value, not a paper param
double cbap_qc_max_boost_ratio = 0.30;
double cbap_qc_h_guard_us = 175.0;       // measured worst case, quantised
double cbap_qc_app_hard_delay_us = 838.86;
string cbap_qc_trace_file;
static FILE *cbap_qc_trace_csv = NULL;
''' + a)

b='''			else if(key.compare("CBAP_PFC_AUDIT_FILE")==0)
				conf>>cbap_pfc_audit_file;'''
assert s.count(b)==1
s=s.replace(b, b+'''
			else if(key.compare("CBAP_QUEUE_CONTROLLER_ENABLE")==0)
				conf>>cbap_queue_controller_enable;
			else if(key.compare("CBAP_QC_SOFT_FRACTION")==0)
				conf>>cbap_qc_soft_fraction;
			else if(key.compare("CBAP_QC_MAX_BOOST_RATIO")==0)
				conf>>cbap_qc_max_boost_ratio;
			else if(key.compare("CBAP_QC_H_GUARD_US")==0)
				conf>>cbap_qc_h_guard_us;
			else if(key.compare("CBAP_QC_APP_HARD_DELAY_US")==0)
				conf>>cbap_qc_app_hard_delay_us;
			else if(key.compare("CBAP_QC_TRACE_FILE")==0)
				conf>>cbap_qc_trace_file;''')

c='	config.delayCreditEnable = (cbap_delay_credit_enable != 0);'
assert s.count(c)==1, s.count(c)
s=s.replace(c,'''	config.queueControllerEnable = (cbap_queue_controller_enable != 0);
	config.qcSoftFraction = cbap_qc_soft_fraction;
	config.qcMaxBoostRatio = cbap_qc_max_boost_ratio;
	config.qcHGuardS = cbap_qc_h_guard_us * 1e-6;
	config.qcAppHardDelayS = cbap_qc_app_hard_delay_us * 1e-6;
	config.qcOnWirePacketBytes = cbap_max_wire_packet_bytes;
	// Mutually exclusive: both scale the same capacity, so running them
	// together would double-count the congestion response.  The credit path is
	// EXPERIMENTAL/NOT VALID and must not be revived alongside the controller.
	if (cbap_queue_controller_enable != 0 && cbap_delay_credit_enable != 0)
		ConfigError("CBAP_QUEUE_CONTROLLER_ENABLE and "
			"CBAP_DELAY_CREDIT_ENABLE are mutually exclusive");
''' + c)
io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(s)
print("globals=%d keys=%d push=%d exclusion=%d"
      % (s.count("cbap_queue_controller_enable"),
         s.count('"CBAP_QUEUE_CONTROLLER_ENABLE"'),
         s.count("config.queueControllerEnable"),
         s.count("mutually exclusive")))
