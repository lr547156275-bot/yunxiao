import io
ph='/work/simulation/src/point-to-point/model/rdma-hw.h'
h=io.open(ph,encoding='utf-8',errors='surrogateescape').read()
if h.count("qcPendingEtaNs")==0:
    a='''		uint32_t qcActiveSenders;       // census used for the margin'''
    assert h.count(a)==1
    h=h.replace(a, a+'''
		uint64_t qcPendingEtaNs;        // when the pending command takes effect
		uint64_t qcDrainCommandedBps;   // pending drain half of the signed target
		bool qcDescending;              // a lowering command is in flight
		bool qcRearmRequired;           // positive boost locked out until rearm''')
    b='''			  qcGuardExceeded(0), qcActiveSenders(0),'''
    assert h.count(b)==1
    h=h.replace(b,'''			  qcGuardExceeded(0), qcActiveSenders(0),
			  qcPendingEtaNs(0), qcDrainCommandedBps(0),
			  qcDescending(false), qcRearmRequired(false),''')
    io.open(ph,'w',encoding='utf-8',errors='surrogateescape').write(h)
print("state fields added:", h.count("qcPendingEtaNs"))
