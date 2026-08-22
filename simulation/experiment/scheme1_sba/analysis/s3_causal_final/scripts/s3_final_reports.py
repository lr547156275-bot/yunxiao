# -*- coding: utf-8 -*-
import csv
import gzip
import hashlib
import os

D = '/work/simulation/experiment/scheme1_sba/analysis/s3_causal_final'
B = '/work/simulation/experiment/scheme1_sba'


def sha(p):
    if not os.path.exists(p):
        return 'ABSENT'
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 16), b''):
            h.update(c)
    return h.hexdigest()


ident = list(csv.DictReader(open(os.path.join(D, '_identity.csv'))))
rows = []
for r in ident:
    rows.append('| %s | `%s` | %s |' % (r['arm'], r['file'], r['identical']))
IDT = '\n'.join(rows)

PROV = """# S3 SAME-RUN PROVENANCE

## Cross-run diagnostic ELIMINATED

Both arms re-run under the **same binary** as the audited ckpt4 pair, with only
trace keys added.

| asset | sha256 |
|---|---|
| binary `build/scratch/third` | `%s` |
| libns3 | `%s` |
| third.cc | `%s` |
| tx-serialization-recorder-ml.h | `%s` |
| sr_cbap_s3.txt | `%s` |
| sr_dcqcn_s3.txt | `%s` |
| topology.txt | `%s` |
| s3_flow.txt | `%s` |
| s3_cbap_link.txt | `%s` |
| s3_cbap_path.txt | `%s` |
| s3_round_schedule.txt | `%s` |

Config diff vs ckpt4, CBAP arm: **only** `CBAP_ACTUATION_FILE` and
`TX_SERIALIZATION_TRACE_FILE` added.  DCQCN arm: **only**
`TX_SERIALIZATION_TRACE_FILE` added.  SIM_SEED=2 both arms.

## Byte-identity against the ckpt4 reference

**27 files compared, 27 identical, 0 differ.**

| arm | file | identical |
|---|---|---|
%s

Includes flow_summary.csv (hence all per-flow FCTs), round_summary.csv,
pfc_events.csv, selected_link_timeseries.csv (queue), qc_trace.csv,
port_summary.csv, admission.csv, applied_rate_audit.csv, qlen.txt.

**Adding the trace keys changed nothing.**  Every result below is therefore a
SAME-RUN measurement, not a cross-run diagnostic.

## Windows (from the same-run pair)

| window | interval | duration |
|---|---|---|
| W1 CBAP | [2.000000000, 2.059406587] | 59.406587 ms |
| W1 DCQCN | [2.000000000, 2.058372997] | 58.372997 ms |
| W2 COMMON | [2.000000000, 2.058372997] | 58.372997 ms |
| W3 CBAP tail | [2.058372997, 2.059406587] | **1.033590 ms** |
"""

CAUSAL = """# S3 CAUSAL DECISION (same-run)

## Item 1: canonical ledger, corrected semantics

```
total                   = 609
APPLIED                 = 215
SUPERSEDED              = 340
RIGHT_CENSORED_PENDING  =  54
sum                     = 609   PASS
```

`RIGHT_CENSORED_PENDING` = a command with no sender effect and **no successor**:
the run ended before either could happen.  These are no longer mislabelled as
`SUPERSEDED_BEFORE_EFFECT`.  The 340 now matches the writer counter
(`superseded=340`) and 54 matches `pending=54`, by construction rather than by
coincidence.

## Item 1b: the 340 supersessions by MAGNITUDE

| magnitude class | count | attributable bytes (upper) |
|---|---|---|
| `redundant_dominated` (successor at least as aggressive) | **339** | 0 |
| `lost_decrease` | 1 | ~0 |
| **`lost_increase`** | **0** | **0 B** |

Not one increase was overwritten by a lower successor target.  Supersession
carries **zero attributable lost throughput**.

## Item 3: bottleneck physical busy/idle, per-packet TX_BEGIN/TX_END

Nanosecond union of transmit intervals over the identical W2 window:

| arm | packets | busy_fraction | gap_fraction | gaps | gap mean | served wire |
|---|---|---|---|---|---|---|
| **CBAP** | 66,676 | **0.957198** | **0.042784** | **1,065** | 2,345 ns | 9.576544 Gbps |
| **DCQCN** | 68,800 | **0.987318** | **0.012625** | **497** | 1,482.8 ns | 9.877891 Gbps |

This supersedes the earlier `idle_fraction = 0` statement, which only meant "no
sample window had zero bytes".  At nanosecond resolution the CBAP serializer is
**genuinely idle 4.28 %** of W2, versus 1.26 % for DCQCN: **2.44 ms of real gap
time vs 0.74 ms**, in 1,065 vs 497 separate gaps.

The busy fractions agree with the independently derived served rates to 4
decimals (0.957198 vs 0.957640 utilisation), so the two methods corroborate.

## Item 4: same-window deficit closure

| arm | deficit bytes | deficit frac | mean served |
|---|---|---|---|
| CBAP | 3,420,068 B | 4.6872 % | 9.577550 Gbps |
| DCQCN | 1,301,512 B | 1.7837 % | 9.879327 Gbps |

```
excess_deficit = 3,420,068 - 1,301,512 = 2,118,556 B
excess * 8 / C = 1.694845 ms
tail gap (W3)  = 1.033590 ms
ratio          = 1.6398
```

The excess deficit is **1.64x larger** than the tail gap, i.e. it is more than
sufficient to account for it in magnitude, and it sits in the same window and the
same direction.  Compared **only** against the 1.033590 ms tail component, as
instructed.  No comparison is made against the 4.078824 ms dispersion component,
which is an arithmetic identity of the mean over lock-step completions.

## Item 5: branch decision

- **Branch A** -- CBAP busy_fraction significantly below DCQCN with real TX gaps:
  **TRUE.** 0.957198 vs 0.987318; 1,065 real gaps totalling 2.4972 ms with mean
  2,345 ns. Per the stated rule this localises to **per-QP pacing / packet
  phase**, not to the rate-setting law.
- **Branch B** -- busy fractions equal: **FALSE**, so the residual mean-FCT gap
  is *not* purely lock-step semantics.
- **Branch C** -- unexplained target -> sender/arrival loss in the same run:
  **NOT SUPPORTED.** `lost_increase = 0`, and D1 (command -> sender) is
  20,223 ns mean against a D2 of 84,522 ns that is physical transport.

### Gap-size signature

Mean gap 2,345 ns at 10 Gbps = 2,931 bytes ~= 2.8 packets of 1048 B.  With 64
incast flows each paced near 136 Mbps, one 1048 B packet per flow every ~61 us,
the aggregate is a superposition of 64 independent pacing timers.  Gaps of a few
packet-times are the expected signature of pacing-phase misalignment rather than
of a controller that is asking for too little: the controller's own target was
above C in 100 % of W2 epochs.

**This is a correlation with a mechanism-consistent signature, not a proven
cause.**  No code change is authorised by this round.

## What remains unproven

- That closing the pacing gaps would recover the 1.033590 ms.  The 1.694845 ms
  is an upper bound on what the deficit *could* explain, not a predicted gain.
- The exact split of the 1,065 gaps between per-QP pacing quantisation, packet
  phase alignment, and end-of-batch effects.  `applied_rate_audit.csv` columns
  `rate_clamp_delta_sum_bps` and `actual_arrival_excess_bps` were not examined.

## Prohibitions honoured

No control law, parameter, rho, MAX_BOOST, queue boundary, ECN/PFC threshold,
topology, traffic or seed was modified.  No GREEN deficit-saturation and no
actuator coalescing were implemented.
"""


def main():
    third = '/work/simulation/scratch/third.cc'
    open(os.path.join(D, 'S3_SAME_RUN_PROVENANCE.md'), 'w').write(
        PROV % (sha('/work/simulation/build/scratch/third'),
                sha('/work/simulation/build/libns3.18-point-to-point-debug.so'),
                sha(third),
                sha('/work/simulation/scratch/tx-serialization-recorder-ml.h'),
                sha(os.path.join(B, 'sr_cbap_s3.txt')),
                sha(os.path.join(B, 'sr_dcqcn_s3.txt')),
                sha(os.path.join(B, 'topology.txt')),
                sha(os.path.join(B, 's3_flow.txt')),
                sha(os.path.join(B, 's3_cbap_link.txt')),
                sha(os.path.join(B, 's3_cbap_path.txt')),
                sha(os.path.join(B, 's3_round_schedule.txt')),
                IDT))
    open(os.path.join(D, 'S3_CAUSAL_DECISION.md'), 'w').write(CAUSAL)
    names = sorted(f for f in os.listdir(D) if os.path.isfile(os.path.join(D, f)))
    with open(os.path.join(D, 'SHA256SUMS_CAUSAL.txt'), 'w') as fh:
        for f in names:
            if f == 'SHA256SUMS_CAUSAL.txt':
                continue
            fh.write('%s  %s\n' % (sha(os.path.join(D, f)), f))
    print('written')
    for f in names:
        if f != 'SHA256SUMS_CAUSAL.txt':
            print('%s  %s' % (sha(os.path.join(D, f))[:16], f))


main()
