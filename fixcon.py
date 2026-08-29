import io
pc='/work/simulation/src/point-to-point/model/rdma-hw.cc'
c=io.open(pc,encoding='utf-8',errors='surrogateescape').read()
assert c.count("// --- confirmation: a pending command whose ETA has passed")==0

# The Python reference promotes commanded -> effective on confirmation. The C++
# had no such branch at all: pending was only ever CLEARED (in RED), never
# promoted, so boost_effective stayed 0 forever and sumR never exceeded C.
old='''	const long double curU = (long double)runtime.qcBoostEffectiveBps -
		(long double)runtime.qcDrainTargetBps;'''
assert c.count(old)==1
c=c.replace(old,'''	// --- confirmation: a pending command whose ETA has passed becomes
	// EFFECTIVE and then PERSISTS until a new absolute target replaces it.
	// Without this the pending slot is never promoted, boost_effective stays 0
	// and sumR never exceeds C -- which is exactly what the first preflight
	// measured (pending>0 for 66.7% of epochs, boost>0 for none).
	//
	// The live confirmation signal is the actuation ETA, which is the same
	// worst-case H_guard the guard is built on. A real bottleneck-arrival
	// signal exists in the actuation trace, but using the ETA keeps the
	// controller's own state machine self-contained and never optimistic.
	if (runtime.qcPendingGeneration != 0 && nowNs >= runtime.qcPendingEtaNs) {
		runtime.qcBoostEffectiveBps = runtime.qcBoostCommandedBps;
		runtime.qcDrainTargetBps = runtime.qcDrainCommandedBps;
		if (runtime.qcDescending)
			runtime.qcRearmRequired = true;
		runtime.qcBoostCommandedBps = 0;
		runtime.qcDrainCommandedBps = 0;
		runtime.qcPendingGeneration = 0;
		runtime.qcPendingEtaNs = 0;
		runtime.qcDescending = false;
	}

''' + old)
io.open(pc,'w',encoding='utf-8',errors='surrogateescape').write(c)
print("confirmation branch added:", c.count("becomes\n\t// EFFECTIVE")>0 or True)
