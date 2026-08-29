import io
# Publish the active-sender count from the controller call site via the
# read-only snapshot, so third.cc needs no new coupling.
ph='/work/simulation/src/point-to-point/model/rdma-hw.h'
h=io.open(ph,encoding='utf-8',errors='surrogateescape').read()
old='''		uint64_t drainTargetBps, guardExceeded, queueBytes;
		uint32_t zone;'''
assert h.count(old)==1
h=h.replace(old,'''		uint64_t drainTargetBps, guardExceeded, queueBytes;
		uint32_t zone;
		uint32_t activeSenders;   // census the controller used this epoch''')
io.open(ph,'w',encoding='utf-8',errors='surrogateescape').write(h)

pc='/work/simulation/src/point-to-point/model/rdma-hw.cc'
c=io.open(pc,encoding='utf-8',errors='surrogateescape').read()
old2='''	out->zone = it->second.qcZone;
	return true;'''
assert c.count(old2)==1
c=c.replace(old2,'''	out->zone = it->second.qcZone;
	out->activeSenders = it->second.qcActiveSenders;
	return true;''')
# store it in the runtime
old3='''	runtime.qcZone = zone;'''
assert c.count(old3)==1
c=c.replace(old3,'''	runtime.qcZone = zone;
	runtime.qcActiveSenders = activeSenders;''')
io.open(pc,'w',encoding='utf-8',errors='surrogateescape').write(c)

h2=io.open(ph,encoding='utf-8',errors='surrogateescape').read()
old4='''		uint64_t qcGuardExceeded;       // observed H_eff > H_guard, must stay 0'''
assert h2.count(old4)==1
h2=h2.replace(old4, old4+'''
		uint32_t qcActiveSenders;       // census used for the margin''')
old5='''			  qcGuardExceeded(0),'''
assert h2.count(old5)==1
h2=h2.replace(old5,'''			  qcGuardExceeded(0), qcActiveSenders(0),''')
io.open(ph,'w',encoding='utf-8',errors='surrogateescape').write(h2)
print("activeSenders published through the snapshot")
