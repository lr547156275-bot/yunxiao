import io
# Pass the min rate in rather than inventing a static member.
pc='/work/simulation/src/point-to-point/model/rdma-hw.cc'
c=io.open(pc,encoding='utf-8',errors='surrogateescape').read()
old='''		uint64_t pendingExcessBytes, uint32_t activeSenders, bool pfcSafe,
		uint64_t ledgerCountedBurstBytes)'''
assert c.count(old)==1
c=c.replace(old,'''		uint64_t pendingExcessBytes, uint32_t activeSenders, bool pfcSafe,
		uint64_t ledgerCountedBurstBytes, uint64_t minRateBps)''')
old2='''		const long double floorBps =
			(long double)(activeSenders ? activeSenders : 1) *
			(long double)m_minRateStaticBps + (long double)m_minRateStaticBps;'''
assert c.count(old2)==1
c=c.replace(old2,'''		// Total floor = every active sender's MIN_RATE plus the old side's.
		// Passed in: this function is static, so it cannot read m_minRate.
		const long double floorBps =
			(long double)(activeSenders ? activeSenders : 1) *
			(long double)minRateBps + (long double)minRateBps;''')
io.open(pc,'w',encoding='utf-8',errors='surrogateescape').write(c)

ph='/work/simulation/src/point-to-point/model/rdma-hw.h'
h=io.open(ph,encoding='utf-8',errors='surrogateescape').read()
oldh='''		uint64_t pendingExcessBytes, uint32_t activeSenders,
		bool pfcSafe, uint64_t ledgerCountedBurstBytes);'''
assert h.count(oldh)==1
h=h.replace(oldh,'''		uint64_t pendingExcessBytes, uint32_t activeSenders,
		bool pfcSafe, uint64_t ledgerCountedBurstBytes,
		uint64_t minRateBps);''')
io.open(ph,'w',encoding='utf-8',errors='surrogateescape').write(h)
print("minRateBps threaded through; invented member removed:",
      c.count("m_minRateStaticBps")==0)
