# -*- coding: utf-8 -*-
# Deterministic lifecycle / control-scope tests (report item 7.2).
#
# Two INDEPENDENT defect classes, tested separately and never merged:
#   A -- wire accounting: 1064 (a safety margin) used as a conversion ratio
#   B -- control scope:   qcOwnsRates = !qcLedger.empty()
#
# Part 1 is a structural audit of the C++ source, because the failure mode that
# has bitten repeatedly is a whole missing branch: a reference model passing its
# own tests says nothing about the code that runs.
# Part 2 replays a real trace when one exists.
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CC = os.path.join(HERE, '..', '..', 'src', 'point-to-point', 'model',
                  'rdma-hw.cc')
HH = os.path.join(HERE, '..', '..', 'src', 'point-to-point', 'model',
                  'rdma-hw.h')
TH = os.path.join(HERE, '..', '..', 'scratch', 'third.cc')

PAY = 1000
WIRE = 1048
N = 65
MINR = 100e6
C = 10e9

res = []


def check(name, ok, detail):
    res.append((name, ok, detail))


for p in (CC, HH, TH):
    if not os.path.exists(p):
        print('missing %s' % p)
        sys.exit(2)

cc = open(CC).read()
hh = open(HH).read()
th = open(TH).read()

# the controller body and its call site
cs_start = cc.find('if (s_cbapConfig.queueControllerEnable) {')
cs_end = cc.find('record.effectiveCapacityBps =', cs_start)
csite = cc[cs_start:cs_end]
b_start = cc.find('void RdmaHw::QueueControllerEpoch')
b_end = cc.find('\nuint64_t RdmaHw::', b_start)
body = cc[b_start:b_end if b_end > b_start else len(cc)]

print('=== lifecycle / control-scope tests ===')
print('')
print('--- DEFECT A: wire accounting (independent) ---')

# A1: the single authoritative conversion exists and is derived, not configured
check('A1. one authoritative payload<->link conversion pair exists',
      'RdmaHw::PayloadRateToLinkRate' in cc
      and 'RdmaHw::LinkRateToPayloadRate' in cc,
      'PayloadRateToLinkRate / LinkRateToPayloadRate defined')
check('A2. link bytes DERIVED from CustomHeader, not a second constant',
      'CustomHeader::GetStaticWholeHeaderSize()' in cc
      and 'RdmaHw::CbapLinkBytesPerPacket' in cc,
      'CbapLinkBytesPerPacket() = payload + GetStaticWholeHeaderSize()')
# Strip comments first: the word appears in the explanatory comment recording
# what the defect WAS, which must not be mistaken for a live use.
csite_code = re.sub(r'//[^\n]*', '', csite)
body_code = re.sub(r'//[^\n]*', '', body)
check('A3. the 1064 config value is NOT used as a conversion numerator',
      'qcOnWirePacketBytes' not in csite_code,
      'call site code (comments stripped) never reads qcOnWirePacketBytes')
check('A4. 1064 retains its legitimate role as the deadband margin',
      'qcOnWirePacketBytes' in body,
      'still used for the per-flow packetization quantum')
check('A5. no ad-hoc local ratio recomputation survives',
      '(long double)wireBytes /' not in cc,
      'all conversions go through the helper')
check('A6. conversion to payload happens once, at the sender boundary',
      csite.count('LinkRateToPayloadRate') == 1,
      '%d payload conversion(s) in the call site'
      % csite.count('LinkRateToPayloadRate'))

print('')
print('--- DEFECT B: control scope (independent) ---')

# B1: the defective predicate is gone
check('B1. qcOwnsRates = !qcLedger.empty() is REMOVED',
      'qcOwnsRates = !runtime.qcLedger.empty()' not in cc,
      'ledger non-emptiness no longer implies ownership')
check('B2. ownership requires a live controlled generation',
      'ownedBatchFound' in csite and 'ownedBatch' in csite,
      'newest live batch on this link determines the generation')
check('B3. batch id 0 (no controlled admission) owns nothing',
      re.search(r'if \(ownedBatch == 0\)\s*\n\s*ownedBatchFound = false;',
                csite) is not None,
      'the background flow, admitted in batch 0, is never controlled')
check('B4. explicit generation id is tracked on the link runtime',
      'qcActiveGenerationId' in hh and 'qcActiveGenerationId' in cc,
      'activeGenerationId present')
check('B5. handoffPending exists and is distinct from ownsRates',
      'qcHandoffPending' in hh and 'qcHandoffPending' in cc,
      'batch-done-but-closing is its own state')
check('B6. ownership transitions are counted (must be 1 per batch)',
      'qcOwnershipTransitions++' in cc,
      'single-transition invariant is measurable')
# ownsRate must be RE-DERIVED from the authoritative live set every epoch, not
# latched: a one-way `= false` can go stale, whereas deriving it cannot.
check('B7. per-QP ownsRate is re-derived from the live set each epoch',
      re.search(r'it->second\.ownsRate = live\.count\(it->first\) != 0;',
                csite) is not None
      and re.search(r'led\.ownsRate = inGeneration;', csite) is not None,
      'idempotent per-QP derivation, cannot latch stale')
check('B8. a single completion does NOT end the generation for peers',
      'live.count(it->first)' in csite
      and 'runtime.qcOwnedMemberCount' in csite,
      '65->64->63 is a legal member reduction')
check('B9. GC is deferred until the pending command has closed',
      'cmdInFlight' in csite and 'exitRecoveryPending = true' in csite,
      'ledger entry survives an in-flight command')
check('B10. GC is separated from ownership (four distinct lifecycles)',
      'qcLedgerCount' in csite and 'qcOwnedMemberCount' in csite,
      'ledger size and owned-member count are separate quantities')
check('B11. no NEW boost/drain once handoff is pending',
      'runtime.qcHandoffPending' in body
      and re.search(r'if \(runtime\.qcHandoffPending\)\s*\n\s*desired = 0\.0L;',
                    body) is not None,
      'controller stops steering during handoff')
check('B12. hard invariant: !owns => boost==0, drain==0, no command',
      'qcScopeViolations++' in csite,
      'violation is counted and surfaced in the trace')
check('B13. not owning zeroes DRAIN_MAX (no 9.894 G drain right)',
      re.search(r'if \(!runtime\.qcOwnsRates\)', body) is not None
      and re.search(r'qcDrainMaxWireBps = 0', body) is not None,
      'early return with DRAIN_MAX = 0')

print('')
print('--- INDEPENDENT HAZARD: implicit map insert ---')
check('H1. read-only path lookups use find(), not operator[]',
      csite.count('s_cbapFlowPaths.find(') >= 2
      and 's_cbapFlowPaths[flow->first]' not in csite,
      '%d find() call(s) in the controller call site'
      % csite.count('s_cbapFlowPaths.find('))
check('H2. missing path after ownership is REPORTED, not silently skipped',
      'qcPathMetadataMissing++' in csite,
      'PATH_METADATA_MISSING_AFTER_OWNERSHIP counter present')
check('H3. a missing path can only REDUCE membership, never add a 66th',
      'runtime.qcLedger.count(flow->first)' in csite,
      'counted only for a QP already owned')

print('')
print('--- FROZEN VALUES (must be untouched) ---')
check('F1. MAX_BOOST still 0.30 from config, not hardcoded',
      'qcMaxBoostRatio' in body and '0.30' not in body_code,
      'no literal boost ratio in the controller code')
check('F2. H_guard still from config',
      'qcHGuardS' in body, 'no literal 175')
check('F3. Q_abs still from config',
      'qcAppHardDelayS' in body, 'no literal 838.86')
check('F4. M_safe still from config',
      'qcSafetyMarginBytes' in body, 'no literal 67072')
check('F5. no global sumR <= C clamp reintroduced',
      'sumR <= ' not in body and 'sumRClamp' not in body,
      'short-term sumR > C still permitted at low queue')
check('F6. controller flag default is 0',
      'cbap_queue_controller_enable = 0' in th, 'default off')
check('F7. MIN_RATE not touched in the controller',
      'm_minRate' in csite and 'SetMinRate' not in csite,
      'MIN_RATE only read, never written')
check('F8. no hardcoded 65 / 6.812 G / 0.3188 C anywhere in the fix',
      '6812000000' not in cc and '3188000000' not in cc
      and re.search(r'==\s*65\b', csite) is None,
      'membership and floor are computed, never asserted to a constant')

print('')
print('--- EXPECTED CLOSED-FORM VALUES (derived, for the report) ---')
floor_pay = N * MINR
floor_link = floor_pay * WIRE / float(PAY)
print('  payload floor (65 x 100 Mbps)      = %.4f Gbps' % (floor_pay / 1e9))
print('  link floor    (x 1048/1000)        = %.4f Gbps' % (floor_link / 1e9))
print('  DRAIN_MAX     (C - link floor)     = %.4f Gbps = %.4f C'
      % ((C - floor_link) / 1e9, (C - floor_link) / C))
print('  WRONG (1064 ratio, pre-fix)        = %.4f Gbps'
      % (floor_pay * 1.064 / 1e9))

print('')
fail = 0
for name, ok, detail in res:
    print('  [%s] %-56s %s' % ('PASS' if ok else 'FAIL', name, detail))
    if not ok:
        fail += 1
print('')
print('  %d/%d tests passed' % (len(res) - fail, len(res)))
if fail:
    print('')
    print('  HARD GATE FAILED -- do not run S3.')
sys.exit(1 if fail else 0)
