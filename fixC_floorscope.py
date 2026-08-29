# -*- coding: utf-8 -*-
# DEFECT C -- floor membership vs control generation.
#
# Independent of defect A (wire accounting) and defect B (control scope).
#
# After B, ownership correctly tracked the newest controlled batch.  But the
# SAME set was then used for two different jobs:
#   * who must be guaranteed MIN_RATE (the floor), and
#   * who receives boost / drain (the generation).
# Those are different sets.  Measured consequence in the S3 rho=0.90 run:
#   protected_count peaked at 64, not 65   -> floor_wire = 6.7072 G, not 6.8120 G
#   protected_count fell to 0 while still owning (handoffPending)
#                                          -> floor = 0 -> DRAIN_MAX = 1.0000 C
#
# Fix, per the fixed semantics:
#   floorProtectedQps  = every live CBAP flow on the link (background + incast).
#                        Updated ONLY by authoritative admission / completion /
#                        reclaim events -- never by "newest batch", never by
#                        "did it send this epoch", never by ledger emptiness.
#   newGenerationQps   = newest batch only (64 incast).  Boost denominator.
#   oldSideQps         = live flows NOT in the newest batch (the background
#                        flow).  Keeps its existing old-side release semantics
#                        in ReplanCbapSbaMigrationTargets; NOT re-derived here.
#
# The old/new split already exists at rdma-hw.cc:2668-2716
# (oldFlowsByLink / newFlowsByLink on newestBatch, R_old* = (1-eta)*R_old,
# R_new* = C - R_old*).  This patch reuses that same discriminator and does NOT
# touch the allocator, eta, rho, or the nonlinear migration trajectory.
import io
import sys

H = '/workspaces/yunxiao/simulation/src/point-to-point/model/rdma-hw.h'
C = '/workspaces/yunxiao/simulation/src/point-to-point/model/rdma-hw.cc'


def rd(p):
    return io.open(p, encoding='utf-8', errors='surrogateescape').read()


def wr(p, s):
    io.open(p, 'w', encoding='utf-8', errors='surrogateescape').write(s)


def need(hay, needle, n=1, tag=''):
    got = hay.count(needle)
    if got != n:
        print('ANCHOR FAIL [%s]: expected %d, found %d for:\n%s'
              % (tag, n, got, needle[:240]))
        sys.exit(2)


h, c = rd(H), rd(C)

# ------------------------------------------------------------ new state ----
if 'qcFloorProtectedQps' not in h:
    a = '\t\tuint32_t qcOwnedMemberCount;     // owned QPs in the active generation'
    need(h, a, 1, 'h:owned-count')
    h = h.replace(a, '''		uint32_t qcOwnedMemberCount;     // owned QPs in the active generation
		// --- defect C: THREE distinct sets, never conflated ---------------
		// floorProtectedQps: every live CBAP flow on this link that must be
		// guaranteed MIN_RATE -- the background old-side flow included.  It
		// bounds DRAIN_MAX and is independent of who is being steered.
		// newGenerationQps: the newest batch only; the boost denominator.
		// oldSideQps: live flows outside the newest batch (the background
		// flow), whose release semantics stay in
		// ReplanCbapSbaMigrationTargets.
		std::set<uint32_t> qcFloorProtectedQps;
		std::set<uint32_t> qcNewGenerationQps;
		std::set<uint32_t> qcOldSideQps;
		uint32_t qcFloorCount, qcNewGenCount, qcOldSideCount;''')

    b = '\t\t\t  qcLedgerCount(0), qcOwnershipEnterNs(0),'
    need(h, b, 1, 'h:init')
    h = h.replace(b, '''			  qcFloorCount(0), qcNewGenCount(0), qcOldSideCount(0),
			  qcLedgerCount(0), qcOwnershipEnterNs(0),''')

# expose to the trace
if 'floorCount' not in h:
    a = '\t\tuint32_t activeGenerationId, ownedMemberCount, ledgerCount;'
    need(h, a, 1, 'h:snap')
    h = h.replace(a, '''		uint32_t activeGenerationId, ownedMemberCount, ledgerCount;
		uint32_t floorCount, newGenCount, oldSideCount;''')

old = '''	out->ledgerCount = (uint32_t)it->second.qcLedger.size();'''
need(c, old, 1, 'c:acc')
c = c.replace(old, '''	out->ledgerCount = (uint32_t)it->second.qcLedger.size();
	out->floorCount = (uint32_t)it->second.qcFloorProtectedQps.size();
	out->newGenCount = (uint32_t)it->second.qcNewGenerationQps.size();
	out->oldSideCount = (uint32_t)it->second.qcOldSideQps.size();''')

# ------------------------------------------------------------- call site ---
# Build the three sets in one scan, using the SAME newestBatch discriminator
# the migration replanner already uses, so old/new never disagree.
old = '''		std::set<uint32_t> live;
		for (std::map<uint32_t, CbapFlowRuntime>::const_iterator flow =
				s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow) {
			if (!flow->second.active || flow->second.finished ||
					!flow->second.qp || !flow->second.hw)
				continue;'''
need(c, old, 1, 'c:live-build')
c = c.replace(old, '''		// --- defect C: build the THREE sets in one scan --------------------
		// floorProtectedQps is every live CBAP flow on this link, so the
		// background flow keeps its MIN_RATE guarantee for the whole run and
		// DRAIN_MAX can never reach C.  newGenerationQps is the newest batch
		// only.  oldSideQps is the remainder -- the same discriminator
		// ReplanCbapSbaMigrationTargets uses (batchId == newestBatch), so the
		// two never disagree about which side a flow is on.
		runtime.qcFloorProtectedQps.clear();
		runtime.qcNewGenerationQps.clear();
		runtime.qcOldSideQps.clear();
		for (std::map<uint32_t, CbapFlowRuntime>::const_iterator flow =
				s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow) {
			if (!flow->second.active || flow->second.finished ||
					!flow->second.qp || !flow->second.hw)
				continue;
			std::map<uint32_t, std::vector<uint32_t> >::const_iterator fpit =
				s_cbapFlowPaths.find(flow->first);
			if (fpit == s_cbapFlowPaths.end())
				continue;
			if (std::find(fpit->second.begin(), fpit->second.end(), linkId) ==
					fpit->second.end())
				continue;
			// Membership is driven by the authoritative lifecycle flags
			// (active set at admission, finished set only by
			// FinishCbapFlow()), never by this epoch's packet activity.
			runtime.qcFloorProtectedQps.insert(flow->first);
			if (ownedBatchFound && flow->second.batchId == ownedBatch)
				runtime.qcNewGenerationQps.insert(flow->first);
			else
				runtime.qcOldSideQps.insert(flow->first);
		}
		runtime.qcFloorCount = (uint32_t)runtime.qcFloorProtectedQps.size();
		runtime.qcNewGenCount = (uint32_t)runtime.qcNewGenerationQps.size();
		runtime.qcOldSideCount = (uint32_t)runtime.qcOldSideQps.size();

		std::set<uint32_t> live;
		for (std::map<uint32_t, CbapFlowRuntime>::const_iterator flow =
				s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow) {
			if (!flow->second.active || flow->second.finished ||
					!flow->second.qp || !flow->second.hw)
				continue;''')

# The ledger must now carry EVERY floor member, with ownsRate marking only the
# generation members.  Two flags, one entry per floor member.
old = '''			// Only members of the owned generation are protected.  The
			// background flow keeps baseline DCQCN behaviour and is never
			// floored, boosted or drained by the controller.
			if (!ownedBatchFound || flow->second.batchId != ownedBatch)
				continue;
			live.insert(flow->first);
			CbapQpLedger &led = runtime.qcLedger[flow->first];
			led.ownsRate = true;
			led.generationId = ownedBatch;
			led.linkId = linkId;'''
need(c, old, 1, 'c:gen-filter')
c = c.replace(old, '''			// DEFECT C: the ledger holds every FLOOR member, because the
			// floor must cover the background flow too.  ownsRate marks the
			// narrower set that is actually STEERED (the newest batch).  The
			// background flow therefore contributes 100 Mbps to the floor and
			// is never boosted or drained -- it keeps baseline DCQCN
			// behaviour and its old-side release semantics.
			const bool inGeneration = ownedBatchFound &&
				flow->second.batchId == ownedBatch;
			CbapQpLedger &led = runtime.qcLedger[flow->first];
			led.inFloor = true;
			led.ownsRate = inGeneration;
			led.generationId = inGeneration ? ownedBatch : 0;
			led.linkId = linkId;
			if (inGeneration)
				live.insert(flow->first);''')

# GC / ownership exit: a floor member that is no longer live loses BOTH flags.
old = '''			// (2) ownership exit: idempotent, affects THIS QP only and never
			// terminates the generation for its peers.
			it->second.ownsRate = false;'''
need(c, old, 1, 'c:ownership-exit')
c = c.replace(old, '''			// (2) ownership exit: idempotent, affects THIS QP only and never
			// terminates the generation for its peers.  A QP leaves the floor
			// only here -- i.e. only after FinishCbapFlow() marked it
			// finished, or it left the link -- never because a batch ended.
			it->second.ownsRate = false;
			it->second.inFloor =
				runtime.qcFloorProtectedQps.count(it->first) != 0;''')

# --- floor: sum over inFloor, not ownsRate ---------------------------------
old = '''	for (std::map<uint32_t, CbapQpLedger>::const_iterator it =
			runtime.qcLedger.begin(); it != runtime.qcLedger.end(); ++it) {
		if (!it->second.ownsRate)
			continue;
		if (!seen.insert(it->first).second) {
			dup++;
			continue;
		}'''
need(c, old, 1, 'c:floor-loop')
c = c.replace(old, '''	for (std::map<uint32_t, CbapQpLedger>::const_iterator it =
			runtime.qcLedger.begin(); it != runtime.qcLedger.end(); ++it) {
		// DEFECT C: the floor covers the FLOOR set, not the steered set.
		// Summing over ownsRate gave 64 shares (6.7072 G) during overlap and
		// 0 shares (DRAIN_MAX = 1.0 C) once the batch drained.
		if (!it->second.inFloor)
			continue;
		if (!seen.insert(it->first).second) {
			dup++;
			continue;
		}''')

# protected_count must report the floor set (what bounds DRAIN_MAX)
old = '''		runtime.qcProtectedQps = live;
		runtime.qcLedgerCount = (uint32_t)runtime.qcLedger.size();'''
need(c, old, 1, 'c:protected')
c = c.replace(old, '''		// protected_count reports the FLOOR set: that is the quantity which
		// bounds DRAIN_MAX.  The steered set is reported as new_gen_count.
		runtime.qcProtectedQps = runtime.qcFloorProtectedQps;
		runtime.qcLedgerCount = (uint32_t)runtime.qcLedger.size();''')

# ledger field
if 'bool inFloor' not in h:
    a = '''		bool ownsRate;                  // controller_owns_rates for this QP
		bool exitRecoveryPending;'''
    need(h, a, 1, 'h:ledger-fields')
    h = h.replace(a, '''		bool ownsRate;                  // steered by the controller
		// inFloor: must be guaranteed MIN_RATE.  A superset of ownsRate --
		// the background old-side flow is inFloor but never steered.
		bool inFloor;
		bool exitRecoveryPending;''')
    b = '''			  ownsRate(false), exitRecoveryPending(false),
			  generationId(0), linkId(0) {}'''
    need(h, b, 1, 'h:ledger-init')
    h = h.replace(b, '''			  ownsRate(false), inFloor(false),
			  exitRecoveryPending(false),
			  generationId(0), linkId(0) {}''')

# --- boost denominator stays the GENERATION, never the floor set -----------
old = '''			const long double share = runtime.qcLedger.empty() ? 0.0L :
				(long double)(runtime.qcBoostCommandedBps -
					runtime.qcDrainCommandedBps) /
				(long double)runtime.qcLedger.size();'''
need(c, old, 1, 'c:share')
c = c.replace(old, '''			// DEFECT C: the denominator is the GENERATION size (64), not the
			// ledger/floor size (65).  Dividing by 65 would hand a share to
			// the background flow, which must not be steered.
			const uint32_t genSize = runtime.qcNewGenCount;
			const long double share = genSize == 0 ? 0.0L :
				(long double)(runtime.qcBoostCommandedBps -
					runtime.qcDrainCommandedBps) /
				(long double)genSize;''')

# --- floor is the hard lower bound on the total target --------------------
old = '''	if (cWire + desired < floorWire)
		desired = floorWire - cWire;'''
need(c, old, 1, 'c:floor-clamp')
c = c.replace(old, '''	// The total target may never fall below the floor of the FLOOR set.  With
	// the background flow included this is 6.812 G, so DRAIN_MAX is bounded by
	// C - 6.812 G = 3.188 G and can no longer approach C.
	if (cWire + desired < floorWire)
		desired = floorWire - cWire;''')

# --- not owning: still REPORT the floor, but emit nothing ------------------
# The floor set is independent of ownership: the background flow keeps its
# MIN_RATE guarantee for the whole run.  Zeroing the reported floor here made
# it look as though the guarantee had lapsed.  boost/drain/DRAIN_MAX stay 0
# because nothing is being steered -- that is the item 2 invariant.
old = '''		runtime.qcDrainMaxWireBps = 0;
		runtime.qcFloorWireBps = 0;
		runtime.qcFloorPayloadBps = 0;
		runtime.qcZone = 0;'''
need(c, old, 1, 'c:notowning-floor')
c = c.replace(old, '''		runtime.qcDrainMaxWireBps = 0;   // nothing steered => no drain right
		// The floor SET still exists (the background flow is still live and
		// still guaranteed MIN_RATE), so report it rather than zeroing it.
		// DRAIN_MAX stays 0 regardless: no generation, no steering.
		{
			long double fp = 0.0L, fw = 0.0L;
			for (std::map<uint32_t, CbapQpLedger>::const_iterator it =
					runtime.qcLedger.begin();
					it != runtime.qcLedger.end(); ++it) {
				if (!it->second.inFloor)
					continue;
				const long double pay =
					(long double)it->second.minRatePayloadBps;
				const long double rr = it->second.payloadPacketBytes > 0 ?
					(long double)it->second.wirePacketBytes /
					(long double)it->second.payloadPacketBytes : 1.0L;
				fp += pay;
				fw += pay * rr;
			}
			runtime.qcFloorPayloadBps = (uint64_t)fp;
			runtime.qcFloorWireBps = (uint64_t)fw;
		}
		runtime.qcZone = 0;''')

wr(H, h)
wr(C, c)

print('DEFECT C applied')
print('  three sets declared     : floor=%d newgen=%d oldside=%d'
      % (h.count('qcFloorProtectedQps'), h.count('qcNewGenerationQps'),
         h.count('qcOldSideQps')))
print('  floor sums over inFloor : %d' % c.count('if (!it->second.inFloor)'))
print('  boost denom = genSize   : %d' % c.count('genSize == 0 ? 0.0L'))
print('  protected = floor set   : %d'
      % c.count('runtime.qcProtectedQps = runtime.qcFloorProtectedQps'))
