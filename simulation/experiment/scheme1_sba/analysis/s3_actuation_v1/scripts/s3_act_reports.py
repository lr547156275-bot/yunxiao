# -*- coding: utf-8 -*-
# Write the actuation-audit report files.  Read-only w.r.t. experiment data.
import csv
import hashlib
import os

D = '/work/simulation/experiment/scheme1_sba/analysis/s3_actuation_v1'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 16), b''):
            h.update(c)
    return h.hexdigest()


FIELDS = """# S3 ACTUATION FIELD DEFINITIONS

Every semantic below is taken from source, not from the column name.

## qc_trace.csv (written by `SampleCbapQcTrace`, scratch/third.cc:1019)

| column | runtime field | what it actually is | sampling point |
|---|---|---|---|
| `q0` | `qc.q0Bytes` | the controller's OWN epoch queue sample, bytes | `sw->GetEgressQueueBytes(ifIndex)` at epoch entry |
| `q_next` | `queueBytes` arg | the NEXT queue read, same call | passed in at the call site; must not be paired with this row's `q_stop` |
| `q_stop` | `qc.qStopBytes` | max-prefix PREDICTED queue over the H_guard horizon, bytes | derived inside the controller, not a measurement |
| `boost_commanded` | `qc.boostCommandedBps` | controller TARGET increment just issued, wire bps | not yet in effect |
| `boost_effective` | `qc.boostEffectiveBps` | controller target increment whose deadline has passed, wire bps | still a TARGET, not a measured rate |
| `drain` | `qc.drainTargetBps` | target decrement, wire bps | target |
| `sumR_effective` | computed in the writer, line 1029: `capacityBps + boost_effective - drain` | a TARGET CEILING derived from LINK CAPACITY, **not** a sum of sender rates and **not** an achieved rate | writer arithmetic |
| `arrival_safe_wire_bps` | `qc.arrivalSafeWireBps` | controller's conservative PREDICTED arrival envelope, wire bps | prediction |
| `sender_effective_wire_bps` | `qc.senderEffectiveWireBps` | sum of per-QP sender pacing rates the controller believes are in force, wire bps | controller's ledger view |
| `pending_generation` | `qc.pendingGeneration` | id of the generation whose command has not yet been confirmed | ledger state |

**Critical correction.** `sumR_effective = 10 Gbps + boost_effective` is a target
ceiling built on the link capacity constant.  Its mean of 12.2573 Gbps does
**not** mean senders were asked to transmit 122 % of line rate, and it is not
comparable to a served rate.  An earlier statement of mine that framed it that
way was imprecise and is withdrawn.

## Served rate (both arms)

`served_wire_rate` is **DERIVED**, not a trace column:
`8 * tx_bytes_delta / dt` from `selected_link_timeseries.csv`, where
`tx_bytes_delta` counts `p->GetSize()` bytes actually transmitted by the
bottleneck egress.  This is the only rate in this audit that is a measured
bottleneck service rate.

## actuation.csv (writer scratch/third.cc:4760, hook rdma-hw.cc:3103)

Three stages, each wired to a real event:

| stage | fired by | meaning |
|---|---|---|
| `rate_command` | `s_cbapActuationHook(flowId, currentRate, appliedRate)` at rdma-hw.cc:3103 | the controller has issued a new pacing rate for this QP |
| `sender_rate_effect` | `RdmaQpDequeue` on the sending device | the first packet actually paced at the new rate leaves the sender |
| `first_affected_at_bottleneck` / `arrival_at_bottleneck` | `QbbEnqueue` / `EgressDequeue` on the bottleneck egress (`cbap_actuation_egress_if`) | that packet reaches / leaves the bottleneck queue |

Columns: `time_ns, generation, flow_id, old_rate_bps, rate_bps, stage,
delta_prev_stage_ns, delta_from_command_ns, seq`.

## pending_age (DERIVED, and NOT an actuation delay)

`pending_age` = epoch_time - first epoch carrying the same
`pending_generation`.  It measures how long a generation id persists in the
ledger.  It is **not** D1, D2 or D3.  My earlier "89.5 us actuation lag" used
this quantity as if it were a stage delay; that inference was unsupported and is
withdrawn.  Measured here: mean 82,564 ns, p95 165,000 ns.

## Input substitution (declared)

The audited pair `ckpt4_cbap_s3_out` has **no** actuation.csv
(`CBAP_ACTUATION_FILE` absent from its config).  Stage timestamps come from
`rec2_s3_on_out`, justified because:
- all 64 per-flow FCT strings are **bitwise identical** between the two;
- algorithm-relevant config is identical (CC_MODE 30, CBAP_ENABLE 1,
  MIGRATION_ENABLE 1, CORE_INITIAL_RELEASE 1, RATIO 0.90, SIM_SEED 2,
  MAX_BOOST 0.30, H_GUARD 175, Q_abs 838.86, M_safe 67072, MIN_RATE 100Mb/s);
- `CBAP_MIG` = 1050 in both.
Queue/zone/boost and served-rate metrics still come from the audited
`ckpt4_*` pair.
"""

MD = """# S3 ACTUATION DECOMPOSITION

Window: W2 COMMON_OVERLAP = [2.000000000, 2.058372997] s (58.372997 ms).
Units: ns for delays, bytes for deficits, Gbps for rates.

## Two prior conclusions, corrected

1. **"GREEN acceleration is insufficient"** - already withdrawn.  Additionally,
   the evidence I cited for it was itself misstated: `sumR_effective` is
   `link_capacity + boost_effective`, a target ceiling, **not** an aggregate
   sender rate.  "Controller asks for 122 % of line rate" was the wrong reading
   of that field.  See S3_ACTUATION_FIELD_DEFINITIONS.md.

2. **"89.5 us actuation lag is the main cause"** - NOT SUPPORTED and withdrawn.
   That number was `pending_generation` lifetime, not a stage delay.  With real
   stage timestamps the command-to-bottleneck delay is **D3 mean 104,744 ns**,
   and the decomposition below shows the actuation chain is not the binding
   constraint on the service deficit.

## B. Stage timestamps: AVAILABLE

All three stages are present with real per-generation deltas.  No
MISSING_ACTUATION_STAGE_TIMESTAMPS condition.

## C. Stage delays (MEASURED, n = 215 APPLIED generations)

| delay | n | mean | p50 | p95 | max |
|---|---|---|---|---|---|
| **D1** command -> sender effect | 215 | **20,223 ns** | 13,644 | 52,144 | 67,756 |
| **D2** sender -> bottleneck | 215 | **84,522 ns** | 88,449 | 115,130 | 117,779 |
| **D3** command -> bottleneck | 215 | **104,744 ns** | 107,824 | 160,705 | 169,923 |

D2 / D3 = **80.7 %**: the chain is dominated by propagation and queueing of
in-flight data, not by the sender-side command path.

D3 max 169,923 ns < H_guard 175,000 ns: the whole chain fits inside the
configured guard horizon.

## Generation classification (MEASURED, 609 generations)

| class | count | fraction |
|---|---|---|
| APPLIED | 215 | 0.3530 |
| **SUPERSEDED_BEFORE_EFFECT** | **394** | **0.6470** |
| SUPERSEDED_AFTER_EFFECT | 0 | 0 |
| NEVER_OBSERVED | 0 | 0 |
| EXPIRED | 0 | 0 |

Writer end-of-run counters agree: `pending_54`, `inflight_0`,
`unmatched_0`, `superseded_340`, `negative_0`.

## E. Missing-byte integral and counterfactual bounds

`B_deficit = integral(max(0, C - served_wire_rate) dt)` over W2, from real
`tx_bytes_delta`:

| arm | B_deficit | mean served |
|---|---|---|
| CBAP | **3,420,068 B** | 9.5764 Gbps |
| DCQCN | **1,301,512 B** | 9.8781 Gbps |
| **excess (CBAP - DCQCN)** | **2,118,556 B** | |

Serving that excess at line rate takes **1.694845 ms** -- a COUNTERFACTUAL upper
bound on the CCT component attributable to the service shortfall.  For
reference, the measured tail component is 1.033590 ms, i.e. the deficit is large
enough to cover it, but that is a bound, not an attribution.

### Counterfactual ceilings (COUNTERFACTUAL, not predicted gains)

| factor set to zero | upper-bound bytes | as fraction of CBAP B_deficit |
|---|---|---|
| D1 | 5,435,000 | **1.589** |
| D2 | 22,715,000 | **6.642** |

Both exceed 1.0, which means these ceilings are **not binding** and cannot be
used to attribute the deficit.  The construction assumes every nanosecond of
delay is a full-line-rate hole; the measured **idle fraction is 0.000000**, so
that assumption is false and the true recoverable share is far smaller.  These
rows are reported for completeness and must not be read as "D1 explains 159 % of
the gap".

## F. Verdict against the stated decision rules

- D1 explains >= 70 % of missing bytes? **NO.** D1 is only 19.3 % of D3, and its
  counterfactual bound is non-binding.
- D2 dominant and within H_guard? **YES.** D2/D3 = 80.7 %, D3 max 169,923 ns <
  H_guard 175,000 ns.  Per the stated rule this is **not an execution bug**;
  it points at prediction compensation / control lead time.
- SUPERSEDED_BEFORE_EFFECT dominant? **YES, and this is the strongest single
  finding**: 394/609 = **64.70 %** of commands are replaced before they ever
  reach the sender.  The stated rule for this case is to examine update
  frequency, generation replacement, and whether a one-outstanding-target
  discipline is needed.
- Actuation chain explains < 30 %? **Cannot be closed from these data.**  The
  counterfactual bounds are non-binding, so no percentage attribution is
  defensible.  What IS established: the deficit is not idleness (idle = 0) and
  not queue starvation (queue mean 23,957 B, deep inside GREEN).

**Two rules fire simultaneously** (D2-dominant and superseded-dominant).  They
are consistent: commands are issued every 5 us epoch while the chain needs
~105 us to land, so ~2/3 of them are overwritten in flight.

## What is NOT claimed

- No causal attribution of the 0.4236 Gbps service gap to any single stage.
- No claim about the 4.078824 ms dispersion component; that is an arithmetic
  identity of the mean over lock-step completions, not a control-delay effect.
- The 1.033590 ms tail component is *bounded* by the deficit (1.694845 ms) but
  not *explained* by it.
"""


def main():
    open(os.path.join(D, 'S3_ACTUATION_FIELD_DEFINITIONS.md'), 'w').write(FIELDS)
    open(os.path.join(D, 'S3_ACTUATION_DECOMPOSITION.md'), 'w').write(MD)
    names = sorted(f for f in os.listdir(D) if os.path.isfile(os.path.join(D, f)))
    with open(os.path.join(D, 'SHA256SUMS_ACTUATION.txt'), 'w') as fh:
        for f in names:
            if f == 'SHA256SUMS_ACTUATION.txt':
                continue
            fh.write('%s  %s\n' % (sha(os.path.join(D, f)), f))
    print('written')
    for f in names:
        if f != 'SHA256SUMS_ACTUATION.txt':
            print('%s  %s' % (sha(os.path.join(D, f))[:16], f))


main()
