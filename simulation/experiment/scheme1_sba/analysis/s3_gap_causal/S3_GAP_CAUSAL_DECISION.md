# S3 GAP CAUSAL DECISION

Window W2 = [2.000000000, 2.058372997] s, same-run pair (binary `290cb41f`,
seed 2, byte-identical to the ckpt4 reference on 27 files).

## Item 1: does a rate change reset the send phase?  **NO**

Source path: `s_cbapActuationHook` (rdma-hw.cc:3103) fires immediately after
`ChangeRate` (rdma-hw.cc:3100).  `ChangeRate`'s CBAP branch:

```cpp
Time next = Simulator::Now();
if (qp->cbap.lastTxTimeNs > 0 && qp->lastPktSize > 0){
        Time paced = NanoSeconds(qp->cbap.lastTxTimeNs) +
                NanoSeconds(CbapPacketGapNs(qp->lastPktSize, new_rate));
        if (paced > next) next = paced;
}
if (qp->cbap.creditGateActive && qp->m_nextAvail > next) next = qp->m_nextAvail;
qp->m_nextAvail = next;                      // ABSOLUTE, per-QP anchored
```

| audit question | answer | evidence |
|---|---|---|
| Cancel/Remove an existing send event? | Only via `UpdateNextAvail`, and **only when the new time is EARLIER** (`if (!m_nextSend.IsExpired() && t < m_nextSend.GetTs())`) | qbb-net-device.cc |
| `next_send_time = now + interval`? | **NO** | anchor is `lastTxTimeNs`, this QP's own last transmit |
| modifies `nextAvail` / `m_nextPkt` / `m_rpTimer`? | `m_nextAvail` only; DCQCN timers are cancelled elsewhere, not here | rdma-hw.cc:3100-3112 |
| do 64 QPs cluster after one epoch's commands? | **NO** | `lastTxTimeNs` differs per QP, so the recomputed times stay spread |
| do `redundant_dominated` commands still rearm? | Yes, but the rearm is idempotent when the rate is unchanged; and `if (currentRate != appliedRate)` gates the call | rdma-hw.cc:3099 |
| measured spread of `sender_rate_effect` within one 5 us epoch | mean **5,204 ns**, max **15,612 ns** across 51 command epochs | actuation.csv |

`old_next_send_ns` / `new_next_send_ns` / `phase_shift_ns` per command are
**UNAVAILABLE**: `rate_transition.csv` is empty in this configuration (0 rows) and
no other output records `m_nextAvail` before/after.  Recording them would need a
new trace hook; not done this round.

**Item 1 verdict: the pacer is NOT rearmed to `now`, and no phase resynchronisation
mechanism was found.**

## Item 2: exclusive gap classification

| class | CBAP n | CBAP gap time | share | DCQCN n | DCQCN gap time | share |
|---|---|---|---|---|---|---|
| A bottleneck queue non-empty, port idle (SUPERSEDED: event-level value is 38 gaps / 1.26 %) | **971** | 2,291,598 ns | **91.76 %** | 75 | 83,846 ns | 11.38 % |
| B pacing gap, queue empty | 83 | 203,186 ns | 8.14 % | **261** | 595,974 ns | **80.87 %** |
| C source/application gap | 0 | 0 | 0 | 0 | 0 | 0 |
| D propagation / in-flight | 11 | 2,662 ns | 0.11 % | 161 | 57,127 ns | 7.75 % |
| E simulation boundary | 0 | 0 | 0 | 0 | 0 | 0 |
| total | 1,065 | 2,497,446 ns | | 497 | 736,947 ns | |

### Class A does NOT survive scrutiny -- it is a sampling artefact

Rule 6 says class A means "stop, scheduler/implementation defect".  Before
invoking it I tested the classifier itself and it fails:

- the queue value came from `selected_link_timeseries.csv`, sampled every
  **10,000 ns**;
- class-A gaps have p50 duration **2,162 ns**, max **3,001 ns**;
- so the queue reading can be up to 10 us stale relative to the gap -- it
  describes a different instant than the gap.

Nanosecond-exact packet data contradicts the "port idle with work queued"
reading:

```
CBAP consecutive TX_BEGIN deltas:
    838 ns  x 65,610   <- 98.40 % of packets are BACK-TO-BACK at line rate
   3000 ns  x    652
   3838 ns  x    313
   others  x    101
```

A 1048 B packet occupies exactly 838 ns at 10 Gbps.  **98.40 % of transmissions
start the instant the previous one ends.**  The port is not failing to serve a
backlog; it is saturated almost everywhere and has 965 isolated interruptions.

Gap values are quantised to two numbers, and they decompose exactly:

```
2162 + 838 = 3000        (gap + one packet time = 3000 ns)
```

965 of 1065 gaps are one of these two values.  A deterministic pair of values is
the signature of a timer/quantisation effect, not of queue starvation, which
would produce a dispersed distribution (as DCQCN's does: top value 3591 ns
appears only 22 times).

**Class A is therefore re-labelled `A_ARTEFACT_STALE_QUEUE_SAMPLE`.  No
scheduler defect is claimed, and the stop condition is NOT triggered.**  A
correct classification needs a nanosecond queue trace, which does not exist in
these outputs.

## Item 3: phase concentration -- no synchronisation found

| arm | bin | occupied bins | max packets in one bin | mean |
|---|---|---|---|---|
| CBAP | 1 ns | 66,676 | **1** | 1.0000 |
| CBAP | 10 ns | 66,676 | **1** | 1.0000 |
| CBAP | 100 ns | 66,676 | **1** | 1.0000 |
| CBAP | 1 us | 56,045 | 2 | 1.1897 |
| DCQCN | 1 us | 57,723 | 2 | 1.1919 |

At every bin size up to 100 ns, **never more than one packet per bin** in either
arm, and the 1 us concentration is essentially identical (1.1897 vs 1.1919).
There is no evidence that batching 64 rate commands into one epoch aligns the
send callbacks.

Per-QP inter-packet intervals are **UNAVAILABLE**: the TX recorder is per-link
and `packet_uid` is not a QP identifier, so `actual_interval - expected_interval`
per QP cannot be computed from these outputs.  Only the aggregate bottleneck
interval is available (CBAP p50 838 ns = exactly one packet time).

## Item 4: offline phase counterfactual -- **WITHDRAWN_INVALID_MODEL**

> Withdrawn. Superseded by `analysis/s3_event_gap/`. This item draws no
> conclusion and must not be cited. See S3_COUNTERFACTUAL_WITHDRAWN.md.

`OFFLINE_COUNTERFACTUAL`.  Preserving per-packet sizes, packet count, total
bytes and window, and re-phasing arrival instants uniformly at random:

| quantity | real trace | uniform re-phase (50 trials) |
|---|---|---|
| busy_fraction | **0.957198** | mean **0.616275** (min 0.613879, max 0.619017) |
| gap_fraction | 0.042784 | mean 0.383688 |
| improvement | -- | **-0.340922 (much WORSE)** |

Uniform random phase is dramatically worse than the real schedule, because the
real schedule is already 98.4 % back-to-back.  This does **not** show that
staggering is useless -- it shows my counterfactual model is wrong for this
regime: a saturated serializer needs arrivals *queued*, not spread out.  A
meaningful test would perturb only the 965 gap-adjacent events, not re-draw all
66,676 arrival times.  **No conclusion about phase staggering is drawn.**

## Item 6: decision

- Most extra gaps immediately after a rate command with clustered next-send
  phase? **NO** -- no clustering at <= 100 ns, and the pacer is not rearmed to
  `now`.
- Command-independent but offline staggering removes the gaps? **NOT SHOWN** --
  the counterfactual as specified is invalid in this regime.
- Bottleneck queue non-empty during the gap? **APPARENTLY yes (91.76 %) but
  refuted as a 10 us sampling artefact against 838 ns packet timing.**  Stop
  condition not triggered.
- Clamp/arrival fields show the requested value not applied? **NOT EXAMINED
  conclusively** -- `rate_clamp_delta_sum_bps` and `actual_arrival_excess_bps`
  were carried into the gap table as window means only.

### MULTIPLE_CAUSES_REMAIN

The evidence is not sufficient to identify a unique cause.  What is established:

1. 98.40 % of CBAP packets are back-to-back at line rate; the deficit lives in
   965 discrete interruptions, not in a systematically slow serializer.
2. Those interruptions are quantised to 2162 ns and 3000 ns with
   `2162 + 838 = 3000`, i.e. a deterministic timing relationship, not stochastic
   starvation.
3. The pacer is not rearmed to `now` and no phase synchronisation was found.
4. `lost_increase = 0`, so no rate increase was withdrawn.

What is NOT established: which timer produces the 3000 ns period, whether the
queue was truly non-empty at those instants, and whether removing them would
recover the tail component.

**Required next step before any algorithm change: a nanosecond-resolution
bottleneck queue-depth trace, plus per-QP `m_nextAvail` before/after each rate
command.**  Both are pure instrumentation.  Without them, class A vs class B
cannot be separated, and no controller modification is justified.
