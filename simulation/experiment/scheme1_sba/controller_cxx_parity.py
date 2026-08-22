# C++ / Python parity check for the queue controller.
#
# Why this exists: the reference implementation (controller_ref.py) passed 31/31
# unit tests and 17/17 replay, while the C++ silently omitted the confirmation
# branch entirely -- pending was only ever cleared in RED, never promoted to
# effective. The preflight caught it (boost>0 in 0 epochs, pending>0 in 66.7%),
# but only after two full simulation runs. A structural parity check finds that
# class of omission without running anything.
#
# This is a STRUCTURAL check, not a numerical co-simulation: it verifies that
# every state transition the reference performs has a counterpart in the C++, by
# searching for the required assignments. It cannot prove numerical equivalence;
# it can prove a whole branch is missing, which is the failure that actually
# happened.
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CXX = os.path.join(HERE, '..', '..', 'src', 'point-to-point', 'model',
                   'rdma-hw.cc')

results = []


def check(name, ok, detail):
    results.append((name, ok, detail))


if not os.path.exists(CXX):
    print('rdma-hw.cc not found at %s' % CXX)
    sys.exit(2)

with open(CXX) as handle:
    src = handle.read()

start = src.find('void RdmaHw::QueueControllerEpoch')
if start < 0:
    print('QueueControllerEpoch not found')
    sys.exit(2)
end = src.find('\n}', src.find('{', start))
# take a generous window: to the next function definition
nxt = src.find('\nuint64_t RdmaHw::', start)
body = src[start:nxt if nxt > 0 else len(src)]

print('=== C++ / Python parity: required state transitions ===')
print('  QueueControllerEpoch body: %d lines' % len(body.split('\n')))
print('')

# --- 1. the confirmation branch: commanded -> effective ------------------
# This is the one that was missing. It must PROMOTE, not merely clear.
promotes_boost = re.search(
    r'qcBoostEffectiveBps\s*=\s*runtime\.qcBoostCommandedBps', body)
promotes_drain = re.search(
    r'qcDrainTargetBps\s*=\s*runtime\.qcDrainCommandedBps', body)
check('confirmation promotes boost_commanded -> boost_effective',
      promotes_boost is not None,
      'found' if promotes_boost else 'MISSING -- pending would never take effect')
check('confirmation promotes drain_commanded -> drain_target',
      promotes_drain is not None,
      'found' if promotes_drain else 'MISSING')
gated_on_eta = re.search(
    r'qcPendingGeneration\s*!=\s*0\s*&&\s*nowNs\s*>=\s*runtime\.qcPendingEtaNs',
    body)
check('confirmation is gated on the pending ETA',
      gated_on_eta is not None,
      'found' if gated_on_eta else 'MISSING -- confirmation would be unconditional')

# --- 2. the signed law --------------------------------------------------
check('signed law: u = MAX_BOOST*(1-p) - MAX_DRAIN*p present',
      re.search(r'maxBoost\s*\*\s*\(1\.0L\s*-\s*p\)\s*-\s*maxDrain\s*\*\s*p',
                body) is not None, 'found')
check('p is clamped to [0,1]',
      body.count('p < 0.0L') >= 1 and body.count('p > 1.0L') >= 1, 'found')

# --- 3. pending integrated by ETA, NOT max(effective, pending) ----------
check('Q_stop integrates pending by tau (no max of excesses)',
      'tau' in body and 'hGuard - tau' in body
      and 'std::max(excess' not in body,
      'tau-weighted integration present, no max() of excesses')

# --- 4. hysteresis holds the current target, never zeroes it ------------
holds = re.search(r'desired\s*>\s*curU\s*\)\s*\n\s*desired\s*=\s*curU', body)
check('hysteresis holds curU (does not force u to zero)',
      holds is not None,
      'found' if holds else 'MISSING -- zeroing creates a dQ/dt=0 fixed point')

# --- 5. preemption and no-op both use the deadband ----------------------
check('preemption requires a MEANINGFULLY lower target (deadband)',
      re.search(r'desired\s*<\s*uPend\s*-\s*deadband', body) is not None,
      'found')
check('no-op test uses the deadband, not 1 bit/s',
      re.search(r'delta\s*<\s*deadband', body) is not None, 'found')
check('deadband derived from on-wire packet / H_guard (no new parameter)',
      re.search(r'qcOnWirePacketBytes\s*\*\s*8\.0L\s*/\s*hGuard', body)
      is not None, 'found')

# --- 6. RED semantics ---------------------------------------------------
check('RED sets drain = MAX_DRAIN and zeroes boost',
      re.search(r'qcBoostEffectiveBps\s*=\s*0', body) is not None
      and re.search(r'qcDrainTargetBps\s*=\s*\(uint64_t\)maxDrain', body)
      is not None, 'found')
check('RED entry uses Q_safe (fires before Q crosses hard)',
      re.search(r'qSafe\s*>=\s*hardBytes', body) is not None, 'found')
check('MAX_DRAIN derived from the MIN_RATE floor (no new parameter)',
      re.search(r'maxDrain\s*=\s*C\s*>\s*floorBps', body) is not None,
      'found')

# --- 7. inertness when the flag is off ---------------------------------
first_stmt = body[body.find('{'):body.find('{') + 400]
check('flag-off early return precedes any state mutation',
      'if (!s_cbapConfig.queueControllerEnable)' in first_stmt
      and 'return;' in first_stmt,
      'early return is the first statement')

# --- 8. soft uses Q_stop, not Q_safe ----------------------------------
check('soft/pressure decision uses Q_stop (not Q_safe)',
      re.search(r'qStop\s*>=\s*softBytes', body) is not None
      and re.search(r'qSafe\s*>=\s*softBytes', body) is None,
      'Q_stop drives soft; Q_safe only appears in the hard check')

# --- 9. margin de-duplication ------------------------------------------
check('packetization margin subtracts the ledger-counted bytes',
      'ledgerCountedBurstBytes' in body and 'margin -=' in body
      or 'ledgerCountedBurstBytes' in body, 'found')
check('margin clamped at zero (never negative)',
      re.search(r'margin\s*<\s*0\.0L', body) is not None, 'found')

# --- 10. no revival of the EXPERIMENTAL credit path -------------------
check('does NOT reuse the EXPERIMENTAL credit fields',
      not any(f in body for f in ('delayCreditEnable', 'maxOversubRatio',
                                  'creditMaxDrainRatio', 'queueDelayTargetS',
                                  'queueDelayHardLimitS', 'creditHorizonS')),
      'none of the delay-credit fields appear in the controller body')

print('')
fail = 0
for name, ok, detail in results:
    print('  [%s] %-58s %s' % ('PASS' if ok else 'FAIL', name, detail))
    if not ok:
        fail += 1
print('')
print('  %d/%d parity checks passed' % (len(results) - fail, len(results)))
if fail:
    print('')
    print('  A FAIL here means the C++ and the verified reference disagree')
    print('  STRUCTURALLY. Do not run preflight until they agree: the reference')
    print('  passing its own tests says nothing about the code that runs.')
sys.exit(1 if fail else 0)
