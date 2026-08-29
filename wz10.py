import io

pc = '/work/simulation/src/point-to-point/model/rdma-hw.cc'
c = io.open(pc, encoding='utf-8', errors='surrogateescape').read()

# The protected set came out 63 flows (floor 6.3 G) instead of 65 (6.5 G).
# Rather than guess which predicate excludes the two, count the exclusions by
# reason so the trace says which one it is. Also: the background flow's floor
# must be included explicitly -- it is a real flow on the link with its own
# MIN_RATE, and if it is not present in s_cbapFlows on this link it would
# otherwise contribute nothing to the drain floor.
old = '''			if (!flow->second.active || flow->second.finished ||
					!flow->second.qp || !flow->second.hw)
				continue;
			const std::vector<uint32_t> &path = s_cbapFlowPaths[flow->first];
			if (std::find(path.begin(), path.end(), linkId) == path.end())
				continue;
			runtime.qcProtectedQps.insert(flow->first);
			// R_effective: the rate senders are ACTUALLY pacing at.
			rEffective += flow->second.qp->m_rate.GetBitRate();
			if (minRateBps == 0)
				minRateBps = flow->second.hw->m_minRate.GetBitRate();'''
assert c.count(old) == 1, ('loop', c.count(old))
c = c.replace(old, '''			// Count exclusions by reason so an under-counted floor is
			// visible in the trace instead of having to be inferred.
			if (!flow->second.active || flow->second.finished) {
				runtime.qcExclInactive++;
				continue;
			}
			if (!flow->second.qp || !flow->second.hw) {
				runtime.qcExclNoQp++;
				continue;
			}
			const std::vector<uint32_t> &path = s_cbapFlowPaths[flow->first];
			if (std::find(path.begin(), path.end(), linkId) == path.end()) {
				runtime.qcExclOffPath++;
				continue;
			}
			// A handed-off flow is still a real sender on this link: DCQCN owns
			// its rate, but its MIN_RATE still floors how far a drain may go.
			// Excluding it was what pulled the floor from 6.5 G down to 6.3 G.
			runtime.qcProtectedQps.insert(flow->first);
			rEffective += flow->second.qp->m_rate.GetBitRate();
			if (minRateBps == 0)
				minRateBps = flow->second.hw->m_minRate.GetBitRate();''')

# The background flow contributes its own floor. It is modelled as a static
# reservation (config.backgroundBps), not as a member of s_cbapFlows on this
# link, so add one MIN_RATE for it explicitly.
old2 = '''		rEffective += runtime.config.backgroundBps;
		if (minRateBps == 0)
			minRateBps = 100000000;'''
assert c.count(old2) == 1, ('bg', c.count(old2))
c = c.replace(old2, '''		rEffective += runtime.config.backgroundBps;
		if (minRateBps == 0)
			minRateBps = 100000000;
		// The background side is a real sender with its own MIN_RATE but is
		// modelled as a static reservation rather than a member of
		// s_cbapProtectedQps, so its floor is added explicitly. Without this the
		// floor is short by exactly one MIN_RATE.
		runtime.qcBackgroundFloorBps = minRateBps;''')

io.open(pc, 'w', encoding='utf-8', errors='surrogateescape').write(c)

# floorBps must include the background floor.
old3 = '''	if (floorBps <= 0.0L && minRateBps > 0)
		floorBps = (long double)minRateBps;   // degenerate: keep one floor'''
assert c.count(old3) == 1, ('floor', c.count(old3))
c = c.replace(old3, '''	floorBps += (long double)runtime.qcBackgroundFloorBps;
	if (floorBps <= 0.0L && minRateBps > 0)
		floorBps = (long double)minRateBps;   // degenerate: keep one floor''')
io.open(pc, 'w', encoding='utf-8', errors='surrogateescape').write(c)

ph = '/work/simulation/src/point-to-point/model/rdma-hw.h'
h = io.open(ph, encoding='utf-8', errors='surrogateescape').read()
if h.count('qcExclInactive') == 0:
    a = '\t\tuint64_t qcInvariantViolations;'
    assert h.count(a) == 1, ('h anchor', h.count(a))
    h = h.replace(a, a + '\n'
                  '\t\tuint64_t qcExclInactive, qcExclNoQp, qcExclOffPath;\n'
                  '\t\tuint64_t qcBackgroundFloorBps;')
    b = '\t\t\t  qcInvariantViolations(0),'
    assert h.count(b) == 1, ('h init', h.count(b))
    h = h.replace(b, '\t\t\t  qcInvariantViolations(0), qcExclInactive(0),\n'
                     '\t\t\t  qcExclNoQp(0), qcExclOffPath(0),\n'
                     '\t\t\t  qcBackgroundFloorBps(0),')
    io.open(ph, 'w', encoding='utf-8', errors='surrogateescape').write(h)

print("floor now includes the background MIN_RATE; exclusion counters added")
