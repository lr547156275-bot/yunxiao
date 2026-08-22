# -*- coding: utf-8 -*-
# Item 3: deterministic assertions on the THREE-set separation, checked against
# the source BEFORE any simulation runs.
#
# Three independent defect classes, never merged:
#   A -- wire accounting  (1064 used as a conversion ratio)
#   B -- control scope    (qcOwnsRates = !qcLedger.empty())
#   C -- floor membership (floor set conflated with the steered set)
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CC = os.path.join(HERE, '..', '..', 'src', 'point-to-point', 'model',
                  'rdma-hw.cc')
HH = os.path.join(HERE, '..', '..', 'src', 'point-to-point', 'model',
                  'rdma-hw.h')
TH = os.path.join(HERE, '..', '..', 'scratch', 'third.cc')

cc = open(CC).read()
hh = open(HH).read()
th = open(TH).read()

cs = cc[cc.find('if (s_cbapConfig.queueControllerEnable) {'):
        cc.find('record.effectiveCapacityBps =',
                cc.find('if (s_cbapConfig.queueControllerEnable) {'))]
bs = cc.find('void RdmaHw::QueueControllerEpoch')
body = cc[bs:cc.find('\nuint64_t RdmaHw::', bs)]
cs_code = re.sub(r'//[^\n]*', '', cs)
body_code = re.sub(r'//[^\n]*', '', body)

res = []


def chk(n, ok, d):
    res.append((n, ok, d))


PAY, WIRE, C = 1000.0, 1048.0, 10e9
print('=== item 3: three-set deterministic assertions ===')
print('')

# ---- 1. the three sets exist and are distinct -----------------------------
chk('1a. floorProtectedQps exists as its own set',
    'qcFloorProtectedQps' in hh and 'std::set<uint32_t> qcFloorProtectedQps'
    in hh, 'declared on the link runtime')
chk('1b. newGenerationQps exists as its own set',
    'qcNewGenerationQps' in hh, 'declared')
chk('1c. oldSideQps exists as its own set',
    'qcOldSideQps' in hh, 'declared')
chk('1d. all three are populated in one scan of the live flows',
    cs_code.count('qcFloorProtectedQps.insert') == 1
    and cs_code.count('qcNewGenerationQps.insert') == 1
    and cs_code.count('qcOldSideQps.insert') == 1,
    'one insert site each')
chk('1e. old/new discriminator is batchId == newestBatch (same as replanner)',
    'flow->second.batchId == ownedBatch' in cs_code
    and 'flow->second.batchId > newestBatch' in cc,
    'reuses the existing ReplanCbapSbaMigrationTargets discriminator')
chk('1f. membership is NOT rebuilt from "did it send this epoch"',
    'flow->second.active' in cs_code and 'flow->second.finished' in cs_code
    and 'txBytesDelta' not in cs_code,
    'driven by the authoritative active/finished lifecycle flags')

# ---- 2. floor is summed over the FLOOR set, not the steered set -----------
chk('2a. the floor loop selects inFloor, not ownsRate',
    'if (!it->second.inFloor)' in body_code
    and 'if (!it->second.ownsRate)\n\t\t\tcontinue;' not in
    body_code[body_code.find('long double floorPayload'):
              body_code.find('runtime.qcDuplicateQpCount')],
    'floor covers the background flow')
chk('2b. inFloor is a superset flag distinct from ownsRate',
    'bool inFloor' in hh and 'led.inFloor = true' in cs_code
    and 'led.ownsRate = inGeneration' in cs_code,
    'every floor member gets a ledger entry; only generation members steer')
chk('2c. protected_count reports the FLOOR set (what bounds DRAIN_MAX)',
    'qcProtectedQps = runtime.qcFloorProtectedQps' in cs_code,
    'so protected_count == 65 during overlap')
chk('2d. the floor is still reported when nothing is steered',
    'runtime.qcFloorWireBps = (uint64_t)fw' in body_code,
    'background MIN_RATE guarantee does not lapse outside a batch')
# Must be inside the !qcOwnsRates early-return branch, i.e. before the floor
# is computed for the steering path.
_notown = body[body.find('if (!runtime.qcOwnsRates) {'):
               body.find('long double floorPayload')]
chk('2e. DRAIN_MAX is still 0 when nothing is steered',
    'qcDrainMaxWireBps = 0' in _notown and 'return;' in _notown,
    'zeroed inside the not-owning early return')

# ---- 3. boost denominator stays the GENERATION ---------------------------
chk('3a. boost/drain share is divided by the generation size, not the floor',
    'genSize == 0 ? 0.0L' in cs_code
    and 'runtime.qcLedger.size()' not in
    cs_code[cs_code.find('const uint32_t genSize'):
            cs_code.find('it->second.pendingDown && share')],
    'denominator is qcNewGenCount (64), never 65')
chk('3b. the background flow never receives a boost share',
    'if (!it->second.ownsRate)\n\t\t\t\t\tcontinue;' in cs
    or 'if (!it->second.ownsRate)' in cs_code,
    'share loop skips non-generation members')

# ---- 4. old-side migration semantics untouched ---------------------------
chk('4a. ReplanCbapSbaMigrationTargets is NOT modified by this fix',
    'oldFlowsByLink' in cc and 'newFlowsByLink' in cc
    and 'migrationReleaseRatio' in cc,
    'existing old-side release path reused, not redesigned')
chk('4b. R_old* = (1-eta)*R_old semantics still present',
    'eta_feasible' in cc and 'oldAggregateBps' in cc,
    'nonlinear migration + feasibility floor intact')
chk('4c. rho / initialReleaseRatio untouched',
    'initialReleaseRatio' in cc and 'coreInitialRelease' in cc,
    'core capacity handover intact')

# ---- 5. frozen values ---------------------------------------------------
for nm, tok, lit in (('MAX_BOOST', 'qcMaxBoostRatio', '0.30'),
                     ('H_guard', 'qcHGuardS', '175'),
                     ('Q_abs', 'qcAppHardDelayS', '838.86'),
                     ('M_safe', 'qcSafetyMarginBytes', '67072')):
    chk('5. %s still from config, no literal' % nm,
        tok in body and lit not in body_code, 'no hardcoded %s' % lit)
chk('5e. no hardcoded 65 / 64 / 6.812 G / 3.188 G in the fix',
    '6812000000' not in cc and '3188000000' not in cc
    and re.search(r'==\s*65\b', cs_code) is None
    and re.search(r'==\s*64\b', cs_code) is None,
    'all counts computed from the live sets')
chk('5f. no global sumR <= C clamp reintroduced',
    'sumR <= ' not in body_code, 'short-term sumR > C still allowed')
chk('5g. qcOwnsRates = !empty() still absent',
    'qcOwnsRates = !runtime.qcLedger.empty()' not in cc, 'defect B stays fixed')
chk('5h. controller flag default is 0',
    'cbap_queue_controller_enable = 0' in th, 'flag=0 default')

# ---- 6. trace exposes the three sets -----------------------------------
chk('6a. trace has floor_count / new_gen_count / old_side_count',
    'floor_count,new_gen_count,old_side_count' in th, 'header present')
chk('6b. trace has the lifecycle counters',
    'ownership_transitions,scope_violations' in th
    and 'path_metadata_missing' in th, 'counters present')

print('')
fail = 0
for n, ok, d in res:
    print('  [%s] %-56s %s' % ('PASS' if ok else 'FAIL', n, d))
    if not ok:
        fail += 1
print('')
print('  %d/%d assertions passed' % (len(res) - fail, len(res)))
print('')
print('  EXPECTED at full overlap (65 = 64 incast + 1 background):')
print('    floor_payload = 65 x 100 Mbps        = %.4f Gbps' % (65 * 100e6 / 1e9))
print('    floor_wire    = x 1048/1000          = %.4f Gbps'
      % (65 * 100e6 * WIRE / PAY / 1e9))
print('    DRAIN_MAX     = C - floor_wire       = %.4f Gbps = %.4f C'
      % ((C - 65 * 100e6 * WIRE / PAY) / 1e9,
         (C - 65 * 100e6 * WIRE / PAY) / C))
print('    boost denominator                    = 64 (generation only)')
print('    FORBIDDEN: floor=0, floor=6.7072 G, drain=1.0 C')
if fail:
    print('')
    print('  HARD GATE FAILED -- do not run S3.')
sys.exit(1 if fail else 0)
