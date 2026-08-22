# -*- coding: utf-8 -*-
import hashlib
import io
import os

B = '/work/simulation/experiment/scheme1_sba'
OUT = os.path.join(B, 'analysis/s3_gap_snapshot')


def sha(p):
    if not os.path.exists(p):
        return 'ABSENT'
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 16), b''):
            h.update(c)
    return h.hexdigest()


DEC = u"""# S3 GAP-BOUNDARY SNAPSHOT: FOUR-HYPOTHESIS DECISION

Binary `235edfe0...` (rebuilt with the snapshot recorder; source SHAs in
`CHECKPOINT_PROVENANCE/FREEZE_PRE_SNAPSHOT.txt`).  One S3 CBAP controller-ON
cell, seed 2, window W2 = [2.000000000, 2.058372997] s.  No parameter, control
law, queue bound, ECN or PFC setting was changed.

## G-1 bypass check: PASSED

| check | result |
|---|---|
| S1 recorder OFF vs ON, core results | **14/14 byte-identical, 0 differ** |
| `gap_snapshot.csv` exists only in the ON run | confirmed absent when OFF |

The recorder contains no `Simulator::Schedule` / `Cancel` / `Remove`; it reads
`Simulator::Now()` and per-QP state and writes nothing back.

### A self-check finding, reported rather than hidden

The S1 ON run self-reported `ROWS 400000 DROPPED 4188554 GAPS 1033877`.  The
cause was **my S1 test config, not the recorder**: I set the window to
`[0, 2.1 s]`, the whole run, so on a lightly loaded S1 link every idle interval
counted as a gap (1,033,877 of them).  The S3 cell used the correct 58.373 ms
window and reported **`ROWS 138580 DROPPED 0`** -- no truncation.  The S1
snapshot data is therefore used for the OFF/ON equality check only, never for any
verdict.  The `DROPPED` counter existing is what made this visible instead of
silently passing off truncated data as complete.

## Snapshot inventory

| quantity | value |
|---|---|
| rows | 138,580 |
| gaps captured | 1,066 (offline gap count for the same window: 1,065) |
| gap-start / gap-end rows | 69,290 / 69,290 (exactly balanced) |
| QPs per snapshot | min = p50 = max = **65** (all QPs, same instant) |
| distinct `node_id` / `qp_index` / pairs | 65 / 65 / **65** |
| nodes with non-constant `flow_id_ref` | **0** (identity is `(node_id, qp_index)`) |
| gap-start snapshots per QP | 1,066 for every QP |

Identity is structural: `node_id` and `qp_index` never change, unlike
`crfm.flowId`, which is assigned late and read 0 beforehand in earlier rounds.

## F1 RATE_ALLOCATION_UNDERFEED -- **NOT SUPPORTED**

Raw distribution at gap start, over QPs with `bytes_left > 0`:

| quantity | value |
|---|---|
| per-QP `applied_rate` p05 / p50 / p95 | 0.1480 / 0.1480 / 0.1480 Gbps |
| exact value counts at the median gap | **0.148041 Gbps x 64 QPs**, 0.100817 Gbps x 1 QP |
| `sum(applied)` per gap p05 / p50 / p95 | 9.5754 / 9.5754 / 9.5754 Gbps |
| `sum(applied)` as a share of C | **95.75 %** |
| gaps with `sum(applied) < 0.9 C` | 5 of 1,066 (0.47 %) |
| QPs with `applied_rate > 1 Gbps` | 0 |
| `owns_rate = 1` count, and their applied sum | 64, 9.4746 Gbps |

The steered set holds **95.75 % of line rate in aggregate**, so the controller is
not starving the flows of rate.  The uniform 0.148041 Gbps is a genuine equal
split (64 x 0.148041 = 9.4746 G), not a stuck column and not the MIN_RATE floor
(the floor is 0.1048 Gbps on the wire).

`sum(commanded) = 18.28 Gbps` is **not** interpreted as "the controller asked for
18 Gbps": the commanded column is a per-QP target that is not meant to sum to C,
and mixing wire/payload domains is a known hazard in this codebase.  No claim is
made from it.

## F2 PACER_REARM_OR_NEXTAVAIL_BUG -- **NOT SUPPORTED**

| quantity | value |
|---|---|
| `(next_avail - last_tx) - legal_interval(applied_rate)` min / p50 / max | -1 / **0** / 1 ns |
| QPs more than 1,000 ns beyond the legal interval | **0 of 68,970 (0.00 %)** |
| longest run of unchanged `next_avail` while work pending | 7, out of **1,066** snapshots per QP |

`m_nextAvail` sits exactly at `last_tx + 8*1048/applied_rate`, to within 1 ns
rounding, for every pending QP in every gap.  There is **no illegal forward jump
and no stuck pacer**: the pacer is doing precisely what the applied rate tells it
to do.

## F3 ACTIVE_SET_TAIL_COLLAPSE -- **NOT SUPPORTED**

| QPs with `bytes_left > 0` per gap | count |
|---|---|
| 65 (all) | **1,061 gaps** |
| 1 | 5 gaps |
| everything in between (2..64) | **0 gaps** |

p05 = p50 = p95 = 65.  Only **0.47 %** of gaps have <= 2 pending QPs, and those
5 are the window's tail. `active = 1` for 65 QPs at the median gap;
`owns_rate = 1` for 64.  The active set does not collapse.

## F4 QP_PHASE_CLUSTERING -- **SUPPORTED, and it is exact**

Measured on one simultaneous snapshot per gap, so no historical inference is
involved (that flaw is why the previous round's phase reading was withdrawn).

| bucket width | gaps | occupied buckets p50 | max bucket share p50 |
|---|---|---|---|
| 100 ns | 1,061 | 2 | 0.985 |
| 500 ns | 1,061 | 2 | 0.985 |
| 838 ns | 1,061 | 2 | 0.985 |
| 2,162 ns | 1,061 | 2 | 0.985 |
| 3,000 ns | 1,061 | 2 | 0.985 |

Identical concentration at every bucket width from 100 ns to 3,000 ns is the
signature of a degenerate distribution, so I resolved it exactly rather than
reporting the bucket statistic:

| quantity | value |
|---|---|
| distinct `next_avail` values among pending QPs, per gap | min = p50 = p95 = max = **2** |
| largest identical group size, per gap | **64** (p50 and max) |
| gaps where all pending QPs share one value | 0 of 1,061 |

**All 64 steered QPs hold the identical `m_nextAvail`, to the nanosecond.**  The
two distinct values per gap are: the 64-QP steered set, and the single
background QP. Detail at the median gap (id 955636, t = 2,029,010,728):

```
node=65 qp=0  next_avail=2029026116 (now+15388) app=0.1008G owns=0   <- background
node=0  qp=1  next_avail=2029062846 (now+52118) app=0.1480G owns=1
node=1  qp=2  next_avail=2029062846 (now+52118) app=0.1480G owns=1
...
node=63 qp=64 next_avail=2029062846 (now+52118) app=0.1480G owns=1
```

0.985 = 64/65 exactly.  The per-gap spread statistic (p50 = 21,470 ns) is the
distance between those two groups, not dispersion within the steered set.

## Verdict

**`QP_PHASE_CLUSTERING`** is the only one of the four hypotheses the data
supports, and it holds in the strongest possible form: not "clustered into a few
buckets" but **64 QPs sharing one identical nanosecond**.

Mechanism, stated only as far as the evidence goes: all 64 steered QPs receive
the same rate (0.148041 Gbps) and are paced from `last_tx + legal_interval`.
Because they were released synchronously and are paced identically, their
`m_nextAvail` values coincide and stay coincident. The port then serves 64
back-to-back packets and waits for the shared next-avail instant, which is what
produces the quantised 2,162 / 3,000 ns holes with an **empty** bottleneck queue
seen in the previous round (98.74 % of CBAP gap time, `NEXT_AVAIL_FUTURE` 99.86 %
of gap time).

Consistent with, and now explained by, the frozen findings: the arbiter is
work-conserving (`ELIGIBLE_NOT_SELECTED = 0`) and no wakeup is missing
(`WAKEUP_MISSING = 0`) -- with all 64 QPs ineligible at the same instant, there
is nothing for a correct arbiter to select and nothing for a correct wakeup to do.

### Recommended fix (single)

**Per-QP phase spreading of `m_nextAvail` at rate application**: when a QP's rate
is set, offset its next send instant within one packet interval by a
deterministic per-QP amount (e.g. `qp_index * interval / N`) instead of anchoring
every QP to the same computed instant. This changes only the *phase* of each
QP's pacing, not its rate, not the aggregate allocation, and not any queue bound.

Not implemented in this round, per instruction. What an oracle test must show
before adopting it: that spreading recovers a material part of the 1.033590 ms
tail/CCT difference, with `sum(applied)` and all safety metrics unchanged.

### Explicitly not claimed

- That phase spreading will recover the tail. Magnitude sufficiency
  (1.760499 ms of excess gap time >= 1.033590 ms of tail) is not causation, and
  no fix has been tested.
- Any statement about DCQCN's pacer phase. The DCQCN arm was not run in this
  round; it was not needed, because the CBAP verdict is unambiguous.
- Any reading of `sum(commanded) = 18.28 Gbps`.
"""


def main():
    io.open(os.path.join(OUT, 'S3_SNAPSHOT_DECISION.md'), 'w',
            encoding='utf-8').write(DEC)
    names = sorted(f for f in os.listdir(OUT)
                   if os.path.isfile(os.path.join(OUT, f)))
    with io.open(os.path.join(OUT, 'SHA256SUMS_SNAPSHOT.txt'), 'w',
                 encoding='utf-8') as fh:
        for f in names:
            if f == 'SHA256SUMS_SNAPSHOT.txt':
                continue
            fh.write(u'%s  %s\n' % (sha(os.path.join(OUT, f)), f))
    print('written')
    for f in names:
        if f != 'SHA256SUMS_SNAPSHOT.txt':
            p = os.path.join(OUT, f)
            print('  %s  %9d  %s' % (sha(p)[:16], os.path.getsize(p), f))


main()
