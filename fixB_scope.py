# -*- coding: utf-8 -*-
# DEFECT B -- control scope.  Independent of defect A.
#
# rdma-hw.cc:1623 said
#     runtime.qcOwnsRates = !runtime.qcLedger.empty();
# Ledger non-emptiness only means metadata/history exists.  The background flow
# is a permanent CBAP flow that traverses the link forever, so the ledger was
# never empty and the controller believed it owned rates for the whole 3 s run.
# Measured consequence: 384,944 of 399,998 owning epochs had exactly ONE ledger
# member (the background flow), where floor = 1 x 104.8 Mbps and therefore
# DRAIN_MAX = C - floor = 9.894 G = 0.9894 C -- a near-total drain authority
# outside any batch.  That is the 0.9894 C and the sumR min = 0.106 G.
#
# Fix: an explicit ownership lifecycle keyed on the batch, with the four
# lifecycles separated (completion / ownership exit / GC / retire).  No new
# performance state, no tuning, no threshold changes.
#
# AUTHORITATIVE EVENTS USED (none invented, none inferred):
#   admission      : rdma-hw.cc:6664  flow.active = true
#   completion     : FinishCbapFlow() flow.finished = true   (sole site, :4792)
#   batch drained  : FinishCbapFlow()'s existing batchStillActive scan
#   handoff        : qp->cbap.handedOff = true
# So MISSING_AUTHORITATIVE_HANDOFF_EVENT does NOT apply -- reported as such.
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

# ------------------------------------------------------------- new state ----
if 'qcActiveGenerationId' not in h:
    a = '\t\tbool qcOwnsRates;'
    need(h, a, 1, 'h:ownsRates')
    h = h.replace(a, '''		// --- explicit ownership lifecycle (defect B) --------------------
		// controllerOwnsRates is NOT "the ledger is non-empty".  It is true
		// only between the admission of a controlled batch and that batch's
		// authoritative drain/handoff, with all pending commands closed.
		uint32_t qcActiveGenerationId;   // batchId of the owned batch, 0 = none
		bool qcOwnsRates;                // controllerOwnsRates
		bool qcHandoffPending;           // batch done, pending commands closing
		uint32_t qcOwnedMemberCount;     // owned QPs in the active generation
		uint32_t qcLedgerCount;          // ledger size, for GC/audit only
		uint64_t qcOwnershipEnterNs, qcOwnershipExitNs;
		uint32_t qcOwnershipTransitions; // must be exactly 1 per batch
		uint32_t qcScopeViolations;      // command emitted while !ownsRates
		uint32_t qcPathMetadataMissing;  // PATH_METADATA_MISSING_AFTER_OWNERSHIP''')

    b = '\t\t\t  qcOwnsRates(false), qcExitRecoveryPending(false),'
    need(h, b, 1, 'h:init')
    h = h.replace(b, '''			  qcActiveGenerationId(0), qcOwnsRates(false),
			  qcHandoffPending(false), qcOwnedMemberCount(0),
			  qcLedgerCount(0), qcOwnershipEnterNs(0),
			  qcOwnershipExitNs(0), qcOwnershipTransitions(0),
			  qcScopeViolations(0), qcPathMetadataMissing(0),
			  qcExitRecoveryPending(false),''')

# expose to the trace
if 'ownedMemberCount' not in h:
    a = '\t\tbool ownsRates, exitRecoveryPending, inRed;'
    need(h, a, 1, 'h:snap')
    h = h.replace(a, '''		bool ownsRates, exitRecoveryPending, inRed;
		uint32_t activeGenerationId, ownedMemberCount, ledgerCount;
		uint32_t ownershipTransitions, scopeViolations, pathMetadataMissing;
		bool handoffPending;''')

# --------------------------------------------------------------- accessor ---
old = '''	out->ownsRates = it->second.qcOwnsRates;'''
need(c, old, 1, 'c:acc')
c = c.replace(old, '''	out->ownsRates = it->second.qcOwnsRates;
	out->activeGenerationId = it->second.qcActiveGenerationId;
	out->ownedMemberCount = it->second.qcOwnedMemberCount;
	out->ledgerCount = (uint32_t)it->second.qcLedger.size();
	out->ownershipTransitions = it->second.qcOwnershipTransitions;
	out->scopeViolations = it->second.qcScopeViolations;
	out->pathMetadataMissing = it->second.qcPathMetadataMissing;
	out->handoffPending = it->second.qcHandoffPending;''')

# ------------------------------------------------------------- call site ----
# Replace membership + ownership determination wholesale.  The four lifecycles:
#   (1) completion  -- flow.finished, set only by FinishCbapFlow()
#   (2) ownership   -- entry.ownsRate false on completion; generation ends only
#                      when the batch has no live member AND nothing is pending
#   (3) GC          -- ledger entry erased only after its pending command closed
#   (4) retire      -- generation id cleared, controller stops emitting
old = '''		std::set<uint32_t> live;
		for (std::map<uint32_t, CbapFlowRuntime>::const_iterator flow =
				s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow) {
			if (!flow->second.active || flow->second.finished ||
					!flow->second.qp || !flow->second.hw)
				continue;
			const std::vector<uint32_t> &path = s_cbapFlowPaths[flow->first];
			if (std::find(path.begin(), path.end(), linkId) == path.end())
				continue;
			live.insert(flow->first);
			CbapQpLedger &led = runtime.qcLedger[flow->first];
			led.ownsRate = true;'''
need(c, old, 1, 'c:live-build')
c = c.replace(old, '''		// --- (0) which batch, if any, does the controller own? -------------
		// A controlled generation exists only while the NEWEST admitted CBAP
		// batch still has a live member on this link.  "The ledger is
		// non-empty" is not evidence of ownership -- that equivalence is
		// defect B, and it kept the controller running for the whole 3 s run.
		//
		// The discriminator is the batch, NOT the flow's identity: in S3 the
		// background flow (src host 65, pg=0, t=0.5 s) is a first-class member
		// of s_cbapFlows with its own path row, admitted in its own earlier
		// batch, and the 64 incast flows (pg=3, t=1.9 s) arrive later as a
		// separate batch.  Selecting the newest live batch therefore excludes
		// the background flow while the incast batch is running, and excludes
		// EVERYTHING once the incast batch has drained -- which is precisely
		// the 384,944 single-member epochs that produced DRAIN_MAX = 0.9894 C.
		//
		// Deliberately NOT special-cased on flow id, host 65, or a hardcoded
		// member count: the rule is structural.
		uint32_t ownedBatch = 0;
		bool ownedBatchFound = false;
		for (std::map<uint32_t, CbapFlowRuntime>::const_iterator flow =
				s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow) {
			if (!flow->second.active || flow->second.finished ||
					!flow->second.qp || !flow->second.hw)
				continue;
			std::map<uint32_t, std::vector<uint32_t> >::const_iterator pit =
				s_cbapFlowPaths.find(flow->first);
			if (pit == s_cbapFlowPaths.end())
				continue;
			if (std::find(pit->second.begin(), pit->second.end(), linkId) ==
					pit->second.end())
				continue;
			if (!ownedBatchFound || flow->second.batchId > ownedBatch) {
				ownedBatch = flow->second.batchId;
				ownedBatchFound = true;
			}
		}
		// A generation must be a genuine controlled batch: the SBA allocator
		// only grants to batches it admitted, so a batch id of 0 means "no
		// controlled admission happened", and the controller owns nothing.
		if (ownedBatch == 0)
			ownedBatchFound = false;

		std::set<uint32_t> live;
		for (std::map<uint32_t, CbapFlowRuntime>::const_iterator flow =
				s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow) {
			if (!flow->second.active || flow->second.finished ||
					!flow->second.qp || !flow->second.hw)
				continue;
			// (5) Read-only path lookup: find(), never operator[].  An
			// implicit empty insert would corrupt the
			// s_cbapFlows.size() == s_cbapFlowPaths.size() consistency check.
			std::map<uint32_t, std::vector<uint32_t> >::const_iterator pit =
				s_cbapFlowPaths.find(flow->first);
			if (pit == s_cbapFlowPaths.end()) {
				// PATH_METADATA_MISSING_AFTER_OWNERSHIP: only meaningful for a
				// QP we already own; a missing path can only ever explain
				// membership REDUCTION, never an extra member.
				if (runtime.qcLedger.count(flow->first))
					runtime.qcPathMetadataMissing++;
				continue;
			}
			const std::vector<uint32_t> &path = pit->second;
			if (std::find(path.begin(), path.end(), linkId) == path.end())
				continue;
			// Only members of the owned generation are protected.  The
			// background flow keeps baseline DCQCN behaviour and is never
			// floored, boosted or drained by the controller.
			if (!ownedBatchFound || flow->second.batchId != ownedBatch)
				continue;
			live.insert(flow->first);
			CbapQpLedger &led = runtime.qcLedger[flow->first];
			led.ownsRate = true;
			led.generationId = ownedBatch;
			led.linkId = linkId;''')

# --- (1)(2)(3): completion -> ownership exit -> GC, as separate steps -------
old = '''		// A QP leaves the ledger only on completion/reclaim, never because it
		// happened not to send this epoch.  While a last slowdown is still in
		// flight the entry is kept under exit recovery.
		for (std::map<uint32_t, CbapQpLedger>::iterator it =
				runtime.qcLedger.begin(); it != runtime.qcLedger.end(); ) {
			if (live.count(it->first)) {
				++it;
				continue;
			}
			if (it->second.pendingDown &&
					record.deliveryTimeNs < it->second.effectDeadlineNs) {
				it->second.exitRecoveryPending = true;
				++it;                      // keep: command not yet at the neck
				continue;
			}
			runtime.qcLedger.erase(it++);
		}
		runtime.qcProtectedQps = live;
		runtime.qcOwnsRates = !runtime.qcLedger.empty();
		runtime.qcExitRecoveryPending = false;'''
need(c, old, 1, 'c:erase+owns')
c = c.replace(old, '''		// --- (1) completion -> (2) ownership exit -> (3) GC ---------------
		// Three DISTINCT steps.  A QP that finished loses ownsRate immediately
		// (so it stops contributing to the floor and to protected_count), but
		// its ledger entry survives until any in-flight command has closed, and
		// only then is it garbage-collected.  65 -> 64 -> 63 is a legal
		// sequence; each step is driven by FinishCbapFlow()'s finished flag,
		// which is the sole authoritative completion event.
		for (std::map<uint32_t, CbapQpLedger>::iterator it =
				runtime.qcLedger.begin(); it != runtime.qcLedger.end(); ) {
			if (live.count(it->first)) {
				++it;
				continue;
			}
			// (2) ownership exit: idempotent, affects THIS QP only and never
			// terminates the generation for its peers.
			it->second.ownsRate = false;
			const bool cmdInFlight =
				(it->second.pendingUp || it->second.pendingDown) &&
				record.deliveryTimeNs < it->second.effectDeadlineNs;
			if (cmdInFlight) {
				it->second.exitRecoveryPending = true;
				++it;              // (3) GC deferred: command not yet at neck
				continue;
			}
			runtime.qcLedger.erase(it++);
		}
		runtime.qcProtectedQps = live;
		runtime.qcLedgerCount = (uint32_t)runtime.qcLedger.size();
		runtime.qcOwnedMemberCount = (uint32_t)live.size();

		// --- (4) ownership / retire ---------------------------------------
		// DEFECT B was: qcOwnsRates = !qcLedger.empty().  Ownership now
		// requires a live controlled generation.  Any pending command must
		// still close before the controller stops, so the batch's last
		// slowdown is not abandoned mid-flight.
		bool anyPending = false;
		for (std::map<uint32_t, CbapQpLedger>::const_iterator it =
				runtime.qcLedger.begin(); it != runtime.qcLedger.end(); ++it)
			if (it->second.pendingUp || it->second.pendingDown)
				anyPending = true;
		if (runtime.qcPendingGeneration != 0)
			anyPending = true;

		const bool wasOwning = runtime.qcOwnsRates;
		if (ownedBatchFound && !live.empty()) {
			if (!wasOwning) {
				runtime.qcActiveGenerationId = ownedBatch;
				runtime.qcOwnershipEnterNs = record.deliveryTimeNs;
				runtime.qcOwnershipTransitions++;
			}
			runtime.qcOwnsRates = true;
			runtime.qcHandoffPending = false;
		} else if (wasOwning && anyPending) {
			// Batch drained or handed off, but commands are still in flight:
			// stop producing NEW boost/drain, let the ledger close, keep the
			// current effective rate.  Ownership has not yet been released.
			runtime.qcHandoffPending = true;
			runtime.qcOwnsRates = true;
		} else if (wasOwning) {
			runtime.qcOwnsRates = false;
			runtime.qcHandoffPending = false;
			runtime.qcActiveGenerationId = 0;
			runtime.qcOwnershipExitNs = record.deliveryTimeNs;
		} else {
			runtime.qcOwnsRates = false;
			runtime.qcHandoffPending = false;
			runtime.qcActiveGenerationId = 0;
		}
		runtime.qcExitRecoveryPending = false;''')

# --- no new commands once the batch is done ---------------------------------
old = '''		if (runtime.qcPendingGeneration != 0 &&
				runtime.qcCommandTimeNs == record.deliveryTimeNs) {'''
need(c, old, 1, 'c:propagate')
c = c.replace(old, '''		if (runtime.qcPendingGeneration != 0 &&
				!runtime.qcHandoffPending &&
				runtime.qcCommandTimeNs == record.deliveryTimeNs) {''')

# --- hard assertion: nothing is emitted while not owning -------------------
old = '''		long double target = (long double)snapshot.capacityBps +
			(long double)runtime.qcBoostEffectiveBps -
			(long double)runtime.qcDrainTargetBps;'''
need(c, old, 1, 'c:target')
c = c.replace(old, '''		// HARD INVARIANT (item 4): not owning => no boost, no drain, no rate
		// command.  Counted rather than asserted so a violation is visible in
		// the trace instead of aborting a 3 s run.
		if (!runtime.qcOwnsRates &&
				(runtime.qcBoostEffectiveBps != 0 ||
				 runtime.qcDrainTargetBps != 0 ||
				 runtime.qcBoostCommandedBps != 0 ||
				 runtime.qcDrainCommandedBps != 0 ||
				 runtime.qcPendingGeneration != 0))
			runtime.qcScopeViolations++;
		long double target = (long double)snapshot.capacityBps +
			(long double)runtime.qcBoostEffectiveBps -
			(long double)runtime.qcDrainTargetBps;''')

# --- controller: stop producing new commands during handoff ----------------
old = '''	if (runtime.qcExitRecoveryPending && desired > 0.0L)
		desired = 0.0L;               // no upward command during recovery'''
need(c, old, 1, 'c:recovery')
c = c.replace(old, '''	if (runtime.qcExitRecoveryPending && desired > 0.0L)
		desired = 0.0L;               // no upward command during recovery
	// Handoff in progress: the batch is done and the current effective rate is
	// being handed back.  Close out, do not steer.
	if (runtime.qcHandoffPending)
		desired = 0.0L;''')

# --- ledger fields for generation/link membership --------------------------
if 'generationId' not in h.split('struct CbapQpLedger')[1].split('};')[0]:
    a = '''		bool ownsRate;                  // controller_owns_rates for this QP
		bool exitRecoveryPending;'''
    need(h, a, 1, 'h:ledger-fields')
    h = h.replace(a, '''		bool ownsRate;                  // controller_owns_rates for this QP
		bool exitRecoveryPending;
		// Link membership and generation captured AT ownership acquisition, so
		// a later path-metadata loss cannot silently change who is owned.
		uint32_t generationId;
		uint32_t linkId;''')
    b = '''			  ownsRate(false), exitRecoveryPending(false) {}'''
    need(h, b, 1, 'h:ledger-init')
    h = h.replace(b, '''			  ownsRate(false), exitRecoveryPending(false),
			  generationId(0), linkId(0) {}''')

wr(H, h)
wr(C, c)

print('DEFECT B applied')
print('  qcOwnsRates = !empty() remaining : %d (expect 0)'
      % c.count('qcOwnsRates = !runtime.qcLedger.empty()'))
print('  ownership transitions counter    : %d'
      % c.count('qcOwnershipTransitions++'))
print('  scope violation counter          : %d' % c.count('qcScopeViolations++'))
print('  path-missing counter             : %d'
      % c.count('qcPathMetadataMissing++'))
print('  read-only path find()            : %d'
      % c.count('s_cbapFlowPaths.find(flow->first)'))
