# -*- coding: utf-8 -*-
# DEFECT C, second half: the GC predicate.
#
# The three sets were built correctly (verified: floor=65, newGen=64,
# oldSide=1), but the garbage collector still keyed on `live`, which by
# construction holds ONLY generation members:
#       if (inGeneration) live.insert(flow->first);
# So the background flow -- inFloor=true, correctly in floorProtectedQps --
# fell through to erase() on the very same epoch its entry was created.  The
# floor sum then found no inFloor entry and returned 0.
#
# Measured signature (qc_s3_rho090_fixC_out, 30 epochs, t=2.05941-2.059555 s):
#       floor_count=1  old_side_count=1  ledger_count=10  floor_wire=0.0000 G
#       -> DRAIN_MAX = C - 0 = 10.0000 G = 1.0000 C
# floor_count=1 and floor_wire=0 in the same row is the proof: the SET has the
# member, the LEDGER does not.
#
# Fix: GC on floor membership, not on steering membership.  An entry is retired
# only when the QP is in neither set and has no command in flight.  This is the
# "ledger GC separated from controller ownership" requirement -- the two were
# still coupled through `live`.
#
# No thresholds, no parameters, no control-law change.
import io
import sys

C = '/workspaces/yunxiao/simulation/src/point-to-point/model/rdma-hw.cc'


def need(hay, needle, n=1, tag=''):
    got = hay.count(needle)
    if got != n:
        print('ANCHOR FAIL [%s]: expected %d, found %d' % (tag, n, got))
        sys.exit(2)


c = io.open(C, encoding='utf-8', errors='surrogateescape').read()

old = '''		for (std::map<uint32_t, CbapQpLedger>::iterator it =
				runtime.qcLedger.begin(); it != runtime.qcLedger.end(); ) {
			if (live.count(it->first)) {
				++it;
				continue;
			}
			// (2) ownership exit: idempotent, affects THIS QP only and never
			// terminates the generation for its peers.  A QP leaves the floor
			// only here -- i.e. only after FinishCbapFlow() marked it
			// finished, or it left the link -- never because a batch ended.
			it->second.ownsRate = false;
			it->second.inFloor =
				runtime.qcFloorProtectedQps.count(it->first) != 0;
			const bool cmdInFlight =
				(it->second.pendingUp || it->second.pendingDown) &&
				record.deliveryTimeNs < it->second.effectDeadlineNs;
			if (cmdInFlight) {
				it->second.exitRecoveryPending = true;
				++it;              // (3) GC deferred: command not yet at neck
				continue;
			}
			runtime.qcLedger.erase(it++);
		}'''
need(c, old, 1, 'gc-loop')
c = c.replace(old, '''		for (std::map<uint32_t, CbapQpLedger>::iterator it =
				runtime.qcLedger.begin(); it != runtime.qcLedger.end(); ) {
			// (2) ownership exit: idempotent, affects THIS QP only and never
			// terminates the generation for its peers.  Losing ownsRate is
			// NOT losing the floor: the background old-side flow is never
			// steered yet must stay floored for the whole run.
			const bool stillFloored =
				runtime.qcFloorProtectedQps.count(it->first) != 0;
			it->second.inFloor = stillFloored;
			it->second.ownsRate = live.count(it->first) != 0;
			// (3) GC keys on FLOOR membership, not on steering membership.
			// Keying it on `live` -- which holds only generation members --
			// erased the background flow's entry on the same epoch it was
			// created, so the floor sum found nothing and returned 0 while
			// floor_count still reported 1.  That is what made DRAIN_MAX
			// reach 1.0 C for the last 30 epochs of the batch.
			if (stillFloored || it->second.ownsRate) {
				++it;
				continue;
			}
			const bool cmdInFlight =
				(it->second.pendingUp || it->second.pendingDown) &&
				record.deliveryTimeNs < it->second.effectDeadlineNs;
			if (cmdInFlight) {
				it->second.exitRecoveryPending = true;
				++it;              // (4) retire deferred: command in flight
				continue;
			}
			runtime.qcLedger.erase(it++);
		}''')

io.open(C, 'w', encoding='utf-8', errors='surrogateescape').write(c)
print('DEFECT C (GC half) applied')
print('  GC keys on floor membership : %d' % c.count('if (stillFloored || it->second.ownsRate) {'))
print('  live no longer gates GC     : %d' % c.count('if (live.count(it->first)) {'))
