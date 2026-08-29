import io

pc = '/work/simulation/src/point-to-point/model/rdma-hw.cc'
c = io.open(pc, encoding='utf-8', errors='surrogateescape').read()

# The rewritten controller sets qcPendingEtaNs but stopped setting
# qcCommandTimeNs, which the call site now reads to age the pending excess.
# Set both wherever a command is issued.
old = '''			runtime.qcPendingGeneration = runtime.qcGenerationCounter;
			runtime.qcPendingEtaNs = nowNs + (uint64_t)(hGuard * 1e9L);
		}
		return;
	}'''
assert c.count(old) == 1, ('preempt anchor', c.count(old))
c = c.replace(old, '''			runtime.qcPendingGeneration = runtime.qcGenerationCounter;
			runtime.qcCommandTimeNs = nowNs;
			runtime.qcPendingEtaNs = nowNs + (uint64_t)(hGuard * 1e9L);
		}
		return;
	}''')

old2 = '''	runtime.qcPendingGeneration = runtime.qcGenerationCounter;
	runtime.qcPendingEtaNs = nowNs + (uint64_t)(hGuard * 1e9L);
}'''
assert c.count(old2) == 1, ('issue anchor', c.count(old2))
c = c.replace(old2, '''	runtime.qcPendingGeneration = runtime.qcGenerationCounter;
	runtime.qcCommandTimeNs = nowNs;
	runtime.qcPendingEtaNs = nowNs + (uint64_t)(hGuard * 1e9L);
}''')

io.open(pc, 'w', encoding='utf-8', errors='surrogateescape').write(c)
print("qcCommandTimeNs set at %d issue sites" % c.count('qcCommandTimeNs = nowNs'))
