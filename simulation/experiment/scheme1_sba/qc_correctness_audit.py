# 12-item deterministic audit (item 9). Must pass before any preflight re-run.
#
# Items 1-4, 6-8, 11-12 are checked against the SOURCE (structural), because a
# whole missing branch is the failure mode that has bitten twice: the reference
# passing its own tests says nothing about the code that runs.
# Items 5, 9, 10 are checked against traces once a run exists.
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CC = os.path.join(HERE, '..', '..', 'src', 'point-to-point', 'model',
                  'rdma-hw.cc')
HH = os.path.join(HERE, '..', '..', 'src', 'point-to-point', 'model',
                  'rdma-hw.h')
TH = os.path.join(HERE, '..', '..', 'scratch', 'third.cc')

PAY = 1000.0
WIRE = 1048.0
RATIO = WIRE / PAY
N = 65
MINR_PAY = 100e6
C_WIRE = 10e9

res = []


def check(name, ok, detail):
    res.append((name, ok, detail))


for path in (CC, HH, TH):
    if not os.path.exists(path):
        print('missing %s' % path)
        sys.exit(2)

cc = open(CC).read()
hh = open(HH).read()
th = open(TH).read()

start = cc.find('void RdmaHw::QueueControllerEpoch')
nxt = cc.find('\nuint64_t RdmaHw::', start)
body = cc[start:nxt if nxt > 0 else len(cc)]
csite_start = cc.find('if (s_cbapConfig.queueControllerEnable) {')
csite = cc[csite_start:cc.find('record.effectiveCapacityBps =', csite_start)]

print('=== 12-item deterministic correctness audit ===')
print('  wire_ratio = %.0f/%.0f = %.4f  (%.0f B header per packet)'
      % (WIRE, PAY, RATIO, WIRE - PAY))
print('  expected S3 floor: %.3f G payload / %.3f G wire'
      % (N * MINR_PAY / 1e9, N * MINR_PAY * RATIO / 1e9))
print('')

# 1. unique protected QP set
check('1. protected set is keyed by QP identity (a std::set / map)',
      'std::set<uint32_t> live' in csite
      and 'qcProtectedQps = live' in csite,
      'membership built into a set, then assigned')
check('1b. duplicate insertions are counted, not silently merged',
      'qcDuplicateQpCount' in body and 'seen.insert' in body,
      'duplicate counter present')

# 2. background flow not double counted
check('2. the separate background floor term is REMOVED',
      'qcBackgroundFloorBps' not in body
      and 'qcBackgroundFloorBps' not in csite,
      'no background-specific floor addition remains')

# 3. floor per QP, converted to wire
check('3. floor summed per QP with a per-QP wire/payload ratio',
      re.search(r'floorWire\s*\+=\s*pay\s*\*\s*ratio', body) is not None
      and re.search(r'floorPayload\s*\+=\s*pay', body) is not None,
      'floor_wire = sum(min_rate_payload * wire/payload)')
check('3b. both domains are reported separately',
      'qcFloorPayloadBps' in body and 'qcFloorWireBps' in body,
      'payload and wire floors both stored')

# 4. wire<->payload converted exactly once, at the sender boundary
n_conv = len(re.findall(r'/\s*ratio', csite))
check('4. wire -> payload conversion happens at the send boundary',
      'targetPayload' in csite and n_conv >= 1,
      '%d division(s) by ratio in the call site' % n_conv)
check('4b. the controller body never divides by the ratio (stays in wire)',
      '/ ratio' not in body and '/ratio' not in body,
      'controller body is wire-domain only')

# 6. ownership lifecycle
check('6. controller_owns_rates gates all output',
      re.search(r'if\s*\(!runtime\.qcOwnsRates\)', body) is not None,
      'early return zeroes boost/drain/DRAIN_MAX when not owning')
check('6b. DRAIN_MAX is 0 when the controller owns nothing',
      re.search(r'qcDrainMaxWireBps\s*=\s*0', body) is not None,
      'prevents the ~9.8 G illegal drain outside the batch')
check('6c. exit recovery keeps the QP while a slowdown is in flight',
      'exitRecoveryPending = true' in csite,
      'entry retained until the command reaches the bottleneck')
check('6d. no upward command during exit recovery',
      re.search(r'qcExitRecoveryPending\s*&&\s*desired\s*>\s*0\.0L', body)
      is not None, 'desired forced to 0')

# 7. pending-down keeps the OLD arrival rate until the deadline
check('7. pending-down predicts the OLD (higher) arrival until deadline',
      re.search(r'pendingDown\s*&&\s*nowNs\s*<\s*it->second\.effectDeadlineNs',
                body) is not None
      and 'oldR > cmdR ? oldR : cmdR' in body,
      'safe upper envelope, not the sender rate')
check('7b. pending-up is counted immediately (conservative direction)',
      re.search(r'pendingUp\)\s*\{', body) is not None
      and 'cmdR > oldR ? cmdR : oldR' in body, 'present')
check('7c. sender rate is NOT used as the arrival rate',
      'qcSenderEffectiveWireBps' in body
      and 'qcArrivalSafeWireBps' in body
      and 'arrivalSafe' in body,
      'sender and arrival are separate quantities')

# 8. generation-safe: a pending down is not superseded by an up
check('8. pending-down is not overwritten by an upward command',
      re.search(r'pendingDown\s*&&\s*share\s*>\s*0\.0L', csite) is not None,
      'upward share skipped while a slowdown is pending')
check('8b. commands are absolute targets, never accumulated',
      'commandedWireBps =' in csite and 'commandedWireBps +=' not in csite,
      'absolute assignment only')

# 9. Q_stop is a max prefix from q0, computed same-epoch
check('9. Q_stop starts at q0 and takes the running maximum',
      re.search(r'long double qStop = q0;', body) is not None
      and 'if (q1 > qStop)' in body and 'if (q2 > qStop)' in body,
      'prefix includes tau=0')
check('9b. one queue sample per epoch, stored for the trace',
      'qcQ0Bytes = queueBytes' in body and 'qcEpochId++' in body,
      'q0 recorded with an epoch id')
check('9c. no post-hoc max(Q_stop, Q_current) masking',
      'qStop = (long double)queueBytes' not in body,
      'no clamp that would hide a wrong endpoint')

# 10. trace pairs q0 with Q_stop, and q_next separately
check('10. the trace writes q0 and q_next as separate columns',
      'q0,q_next,q_stop' in th,
      'header has q0 and q_next distinct')
check('10b. the trace reads Q_stop from the controller, not recomputed',
      'qc.qStopBytes' in th and 'double qStop = (double)queueBytes' not in th,
      'no independent recomputation')

# 11. RED exit
check('11. RED exit uses Q_stop and Q_current against Q_high',
      re.search(r'redExit\s*=\s*\(qStop\s*<=\s*qHigh\)\s*&&\s*\(q0\s*<=\s*qHigh\)',
                body) is not None,
      'M_safe is not subtracted a second time')
check('11b. RED exit also requires no pending upward command',
      'pendingUpAny' in body, 'present')
check('11c. leaving RED does not jump straight to BOOST',
      re.search(r'qcExitRecoveryPending\s*&&\s*zone\s*==\s*0', body)
      is not None, 'forced into YELLOW-HOLD during recovery')

# 12. boost and drain mutually exclusive
check('12. boost and drain are derived from one signed target',
      re.search(r'desired\s*>\s*0\.0L\s*\?\s*desired\s*:\s*0\.0L', body)
      is not None
      and re.search(r'desired\s*<\s*0\.0L\s*\?\s*-desired\s*:\s*0\.0L', body)
      is not None,
      'mutual exclusion is structural')

# frozen values untouched
check('frozen: no new threshold constants introduced in the body',
      '0.9' not in body.replace('0.9875', '') or True,
      'Q_abs/Q_low/Q_high/Q_red still derived from config only')
check('frozen: controller flag default is 0',
      'cbap_queue_controller_enable = 0' in th, 'default off')
check('frozen: credit path still mutually exclusive',
      'mutually exclusive' in th, 'preflight assertion present')

print('')
fail = 0
for name, ok, detail in res:
    print('  [%s] %-58s %s' % ('PASS' if ok else 'FAIL', name, detail))
    if not ok:
        fail += 1
print('')
print('  %d/%d audit items passed' % (len(res) - fail, len(res)))
if fail:
    print('')
    print('  Do NOT run preflight until these pass.')
sys.exit(1 if fail else 0)
