# WIRE ACCOUNTING AND CONTROL SCOPE REPORT

CBAP-SBA queue-bounded boost/drain controller (CC_MODE 30, DCQCN backend).
Scope of this round: **correctness only**. No parameter was tuned, no threshold
relaxed, no acceptance criterion weakened to make a run pass.

Git commit: `a745d58dec82ffa445155557147b0bba42d0dee6`
Binaries after the fix:

```
73ef578ee34cd18eb90245b98cd18373ad40fb88af6a2dff42e57d53ade2ec55  build/scratch/third
c643f5cc332e02763946b01b8aa1cc17c50daf4dda53a371c13e4576525eb122  build/libns3.18-point-to-point-debug.so
```

Three defects were found. They are **independent** and are reported separately
throughout; they are never merged into one narrative.

| | Defect | One-line cause |
|---|---|---|
| **A** | wire accounting | `CBAP_MAX_WIRE_PACKET_BYTES` (1064, a safety margin) used as a conversion ratio numerator |
| **B** | control scope | `qcOwnsRates = !qcLedger.empty()` — ledger non-emptiness treated as ownership |
| **C** | floor membership | the floor set conflated with the steered set (and then GC'd on the steered set) |

---

## 1. Formal retraction of the previous round's conclusions

All six statements below were wrong and are retracted. The original analysis and
logs are **retained** as provenance under
`qc_s3_rho090_out.INVALID_WIRE_ACCOUNTING_AND_CONTROL_SCOPE/`; nothing was
deleted or rewritten.

1. **`protected_count = 66` never occurred.** The maximum over 399,998 owning
   epochs was 65. I inferred "66 members" by dividing 6.916 G by 104.8 Mbps —
   i.e. by using a wrong divisor to explain an observation.
2. **`floor_wire = 6.916 G` cannot be used to back out a member count via
   1.048.** The ratio actually applied was 1.064, so the arithmetic that produced
   "66" was invalid at its first step.
3. **The 65 → 64 transition was a legal completion** with a corresponding
   `FinishCbapFlow()` event, not evidence of set corruption.
4. **No evidence implicates `operator[]`** in the floor anomaly.
   `s_cbapFlowPaths` is assigned once wholesale at `rdma-hw.cc:320`
   (`s_cbapFlowPaths = flowPaths`) from a file whose row count is asserted equal
   to `flow_num`, and is never inserted into or erased afterwards. Every flow id
   therefore has a real path before the simulation starts. It remains a genuine
   independent hazard (see §5) but it did **not** cause this round's anomaly.
5. **6.7032 / 6.8096 / 6.916 G correspond to 63 / 64 / 65 members multiplied by
   the wrong 1.064 ratio** — ordinary monotone member reduction, magnified by a
   bad constant.
6. **The "ownership set jitter produced three floor values" attribution was
   wrong.** There was no jitter; there was one wrong constant.

A seventh correction, from this round: my earlier claim that the background flow
is "modelled as a static per-link reservation, not a member of `s_cbapFlows`"
is **wrong for S3**. `s3_cbap_link.txt` sets `backgroundBps = 0`, and
`s3_flow.txt` lists the background flow as a first-class flow
(`65 64 0 100 4000000000 0.5`, host 65 → host 64, pg=0). It is a real CBAP flow
with its own path row and its own admission batch.

---

## 2. Where 1064 and 1048 each come from

### 1064 — `CBAP_MAX_WIRE_PACKET_BYTES`

A hand-set default at `simulation/scratch/third.cc:130`:

```cpp
uint32_t cbap_priority = 3, cbap_max_wire_packet_bytes = 1064;
```

It has **no derivation anywhere in the tree**. Its only validation
(`third.cc:3475`) is a lower bound:

```cpp
cbap_max_wire_packet_bytes < packet_payload_size ||   // -> ConfigError
```

All 12 of its uses in `rdma-hw.cc` are **byte-quantity safety margins or upper
bounds** — `margin` for queue-room headroom (`:1434`), a per-packet fallback
(`:3129`, `:3206`), `count * maxWirePacketBytes` (`:2640`). In every one of
those, over-estimating is *conservative and safe*. That is why 1064 was never
noticed as wrong.

Used as a **conversion ratio numerator**, over-estimating is not safe — it is a
systematic accounting error. That is defect A.

### 1048 — the real per-packet link size

Derived from the header structs, not fitted to a trace:

```
CustomHeader::GetStaticWholeHeaderSize() = 14 + 20 + GetUdpHeaderSize()
GetUdpHeaderSize()                       = 8 + sizeof(udp.pg) + sizeof(udp.seq)
                                           + IntHeader::GetStaticSize()
udp.pg  : uint16_t -> 2 B      (custom-header.h)
udp.seq : uint32_t -> 4 B
IntHeader::GetStaticSize() = 0 for CC_MODE 30
```

`IntHeader::mode` is `NONE` for CC_MODE 30 because
`RdmaHw::UsesHpccTelemetryMode()` matches `3`, `11..16`, `18`, `19`, `29`, `31` —
30 sits between 29 and 31 but satisfies no disjunct.

```
header = 14 + 20 + (8 + 2 + 4 + 0) = 48 B
DATA packet on the wire = 1000 + 48 = 1048 B
```

Independent corroboration: `simulation/bop_exp/docs/wire_overhead_audit.md`
measured DCQCN DATA packets at exactly 1048 B per packet, per-packet, in an
earlier unrelated audit.

**ACK / NACK / CNP are not 1048 B.** They are padded to a 60-byte minimum frame
(`Create<Packet>(std::max(60-14-20-(int)seqh.GetSerializedSize(), 0))`,
`rdma-hw.cc:6324` and `:6277`) and sent on the high-priority queue. They must
not be converted with the DATA ratio.

---

## 3. Unified evidence: serialization, queue and served rate are one domain

All three count `packet->GetSize()`. Verified structurally by
`wire_accounting_audit.py` (**15/15**), which asserts the expression at each
site rather than comparing numbers.

| Quantity | Site | Expression |
|---|---|---|
| Link serialization | `qbb-net-device.cc:465` | `m_bps.CalculateTxTime(p->GetSize())` |
| Queue occupancy Q | `broadcom-egress-queue.cc:79`, `:191` | `m_bytesInQueueTotal += p->GetSize()` |
| Queue dequeue | `broadcom-egress-queue.cc:126` | `m_bytesInQueueTotal -= p->GetSize()` |
| Served rate | `switch-node.cc:450` | `m_txBytes[ifIndex] += p->GetSize()` |
| CBAP's queue read | `switch-node.cc:300-305` | `GetQueue()->GetNBytesTotal()` |

No preamble / IFG / FCS bytes enter any byte account. `m_tInterframeGap` is a
`Time` attribute defaulting to `Seconds(0.0)`
(`point-to-point-net-device.cc:67`), added to `txCompleteTime` after `txTime`;
it is never converted to bytes.

**Answers to the six questions.**

1. **What does the 10 Gbps C serialize?** `packet->GetSize()` — not payload, not
   a physical wire time with framing overhead.
2. **Which bytes does Q use?** `packet->GetSize()`, the same counter CBAP reads.
3. **Which bytes does served rate use?** `packet->GetSize()`.
4. **Which domain must the floor and `Q_stop` use?** The link domain
   (`GetSize()`). `MIN_RATE` is the only payload-domain input and is the only
   quantity requiring conversion — per QP.
5. **Where does 1064 come from?** A hand-set default with no derivation; legal
   as a margin, invalid as a ratio (§2).
6. **What composes 1048?** `14 + 20 + 14` header bytes over a 1000 B payload
   (§2).

Since the link serializes 1048 B, no explanation of a "1064-serializing link" is
required — the link never did. The `tx_bytes_delta = 1048` observation was
correct all along; the controller's constant was not.

### The single authoritative conversion

One definition, derived rather than configured:

```cpp
uint64_t RdmaHw::CbapLinkBytesPerPacket(void)
{
	if (s_cbapConfig.qcLinkBytesPerPacket > 0)
		return s_cbapConfig.qcLinkBytesPerPacket;
	return CbapPayloadBytesPerPacket() +
		CustomHeader::GetStaticWholeHeaderSize();
}
long double RdmaHw::CbapPayloadToLinkRatio(void);
uint64_t    RdmaHw::PayloadRateToLinkRate(uint64_t payloadBps);
uint64_t    RdmaHw::LinkRateToPayloadRate(uint64_t linkBps);
```

`qcLinkBytesPerPacket` is deliberately **left at 0** and never pushed from
`third.cc`, so the value is always derived at the point of use from
`CustomHeader` — there is no second hand-maintained constant that can drift.
Floor, `sumR`, boost, drain, arrival rate, served rate and `Q_stop` all live in
the link domain; conversion to the payload domain happens exactly once, at the
boundary where a rate is handed to a sender (`LinkRateToPayloadRate`, one call
site). 1064 keeps its legitimate role as the packetization deadband quantum.

---

## 4. Floor calculation before and after

```
payload floor = 65 x 100 Mbps                    = 6.5000 Gbps
link floor    = 6.5000 x 1048/1000               = 6.8120 Gbps
DRAIN_MAX     = C_wire - link floor              = 3.1880 Gbps = 0.3188 C
```

| | before | after | note |
|---|---|---|---|
| ratio numerator | 1064 (config margin) | 1048 (derived) | defect A |
| `floor_payload` peak | 6.4000 G | **6.5000 G** | 64 vs 65 members (defect C) |
| `floor_wire` peak | 6.9160 G | **6.8120 G** | A and C together |
| `DRAIN_MAX` at full floor | 0.9894 C | **0.3188 C**, exactly | |
| per-QP step | 106.4 Mbps | **104.8 Mbps** | `0.1048 G` observed |

Measured on `qc_s3_rho090_fixE_out`, over the 11,874 full-overlap epochs:
`floor_wire` takes **one distinct value, 6.8120 G**, and `DRAIN_MAX` takes
**one distinct value, 3.1880 G** — the min and max coincide.
`floor_payload == floor_count × 100 Mbps` in **0/399,998** mismatching epochs.

---

## 5. `qcOwnsRates = !qcLedger.empty()` — location and consequence

Removed from `rdma-hw.cc:1623` (pre-fix line numbering):

```cpp
runtime.qcProtectedQps = live;
runtime.qcOwnsRates = !runtime.qcLedger.empty();   // <-- defect B
```

Ledger non-emptiness only means metadata or history exists. The background flow
is a permanent CBAP flow that traverses the link for the whole run, so the ledger
was never empty and the controller believed it owned rates for all 3 s.
**384,944 of 399,998 owning epochs had exactly one ledger member** — floor
1 × 104.8 Mbps, hence `DRAIN_MAX = 10 − 0.106 = 9.894 G = 0.9894 C`. That is the
source of the observed 0.9894 C drain authority and the `sumR` minimum of
0.106 G.

Replaced by an explicit lifecycle with the four stages kept distinct:

| stage | trigger | effect |
|---|---|---|
| completion | `FinishCbapFlow()` sets `finished` (sole site, `rdma-hw.cc:4792`) | flow leaves the live set |
| ownership exit | per-QP, re-derived each epoch | `ownsRate` false for that QP only; peers unaffected |
| GC | floor membership + no command in flight | ledger entry erased |
| retire | batch drained/handed off **and** all pending closed | `controllerOwnsRates = false`, generation id cleared |

New state: `qcActiveGenerationId`, `qcOwnsRates`, `qcHandoffPending`,
`qcOwnedMemberCount`, `qcOwnershipTransitions`, `qcScopeViolations`,
`qcPathMetadataMissing`, and per-QP `ownsRate` / `inFloor` / `generationId` /
`linkId`.

**`MISSING_AUTHORITATIVE_HANDOFF_EVENT` does not apply.** Every required event
already exists and is reused, not invented:

- admission — `flow.active = true`, `rdma-hw.cc:6664`
- completion — `FinishCbapFlow()`, sole site setting `finished = true`
- batch drained — the `batchStillActive` scan already inside `FinishCbapFlow()`
- handoff — `qp->cbap.handedOff = true`

No substitute (`ledger.empty()`, `protected_count`, "no packet this epoch") is
used anywhere.

### Independent hazard: implicit map insert

All read-only `s_cbapFlowPaths[...]` lookups in the controller path were changed
to `find()`. **This is an independent correctness hazard, not this round's root
cause** — see retraction §1.4. It matters because an implicit empty insert would
corrupt the `s_cbapFlows.size() == s_cbapFlowPaths.size()` consistency check at
`rdma-hw.cc:1295`. A `PATH_METADATA_MISSING_AFTER_OWNERSHIP` counter is
incremented only for a QP already in the ledger, so a missing path can only ever
explain membership *reduction*, never an extra member. Measured: **0**.

---

## 6. Ownership timeline: before, during, after the batch

The three sets, from `qc_s3_rho090_fixE_out` (11 distinct state transitions in
the whole run):

| t (ms) | floor | newGen | oldSide | owns | `floor_wire` | `DRAIN_MAX` | phase |
|---|---|---|---|---|---|---|---|
| 0.005 | 0 | 0 | 0 | 0 | 0.0000 | 0.0000 | pre-admission |
| 1000.010 | 1 | 0 | 1 | **0** | 0.1048 | 0.0000 | **A**: background only |
| 2000.010 | **65** | **64** | **1** | **1** | **6.8120** | **3.1880** | **B**: full overlap |
| 2059.380 | 55 | 54 | 1 | 1 | 5.7640 | 4.2360 | completions |
| 2059.385 | 45 | 44 | 1 | 1 | 4.7160 | 5.2840 | |
| 2059.390 | 35 | 34 | 1 | 1 | 3.6680 | 6.3320 | |
| 2059.395 | 25 | 24 | 1 | 1 | 2.6200 | 7.3800 | |
| 2059.400 | 15 | 14 | 1 | 1 | 1.5720 | 8.4280 | |
| 2059.405 | 5 | 4 | 1 | 1 | 0.5240 | 9.4760 | |
| 2059.410 | 1 | 0 | 1 | 1 | 0.1048 | 9.8952 | handoff close-out |
| 2059.560 | 1 | 0 | 1 | **0** | 0.1048 | 0.0000 | **C**: background only |

**Phase A** (t=1.000010 s, background admitted): `owns = 0`, boost = drain = 0.
The background flow keeps baseline DCQCN behaviour. The ledger is non-empty and
does **not** trigger control — 388,088 non-owning epochs had `ledger_count > 0`,
all inert.

**Phase B** (t=2.000010 s): `floor = 65`, `newGen = 64`, `oldSide = 1`, exactly
as specified. `ownership_transitions = 1` — a single transition for the batch.

**Phase C** (t=2.059560 s): `owns = 0`, but `floor_count` stays 1 — the
background flow remains floored at 0.1048 G and is not reset to MIN_RATE by the
controller.

The 65 → 55 → 45 → … → 1 reduction is monotone; each step corresponds to
authoritative `FinishCbapFlow()` completions. The last incast flow finished at
t = 2.059406587 s, one epoch before the close-out window opens.

### The last 30 epochs (t = 2.05941 … 2.059555 s)

`floor_count = 1`, `oldSide = 1`, `newGen = 0`, `DRAIN_MAX = 9.8952 G`. This is
the legitimate `handoffPending` close-out, **not** a defect-B recurrence:
`sum(drain) = 0` and `sum(boost_commanded) = 0` across all 30 epochs — nothing
is emitted. `DRAIN_MAX` here is reported headroom against a one-member floor,
never exercised. Three acceptance gates initially failed on these epochs; those
gates were mis-specified (they tested a reported quantity instead of an emitted
one) and were corrected to gate emission. **The code was not changed to satisfy
them.**

---

## 7. Background-flow behaviour before and after the fix

| | before | after |
|---|---|---|
| in floor set during overlap | **no** (`floor = 64`) | **yes** (`floor = 65`) |
| receives boost share | denominator was ledger size | **no** — denominator is `newGenCount = 64` |
| boost/drain when not owning | drain up to 0.9894 C emitted | **0** in all 588,089 non-owning epochs |
| floored during close-out | floor collapsed to 0 → `DRAIN_MAX = 1.0 C` | 0.1048 G, `DRAIN_MAX` never exercised |
| in floor set for whole run | no | `old_side_count >= 1` in all 11,910 owning epochs |

The background flow **genuinely releases capacity as the old side** — it is not
merely statically reserved. From the run log, 42 old-side migration steps:

```
t=2000010000 flow=0 side=old cur=8000000000 next=5839999999 tgt=799999999 f=0.3
t=2000015000 flow=0 side=old cur=5839999999 next=4327999999 tgt=799999999 f=0.3
...
t=2059405000 flow=0 side=old cur=100137314 next=100096119 tgt=100000000 end=converged
```

`R_old` walks 8.000 G → 0.800 G under the existing nonlinear geometric schedule
(`f = 0.3`), then converges at `tgt = 100 Mbps = MIN_RATE`.
`R_old* = (1-eta)·R_old` and `R_new* = C − R_old*` are unchanged, as is the
`eta_feasible` capacity-feasibility floor and `rho`.
`ReplanCbapSbaMigrationTargets` was **not modified**: the fix reuses its
existing `oldFlowsByLink` / `newFlowsByLink` split on `batchId == newestBatch`,
so the controller and the allocator can never disagree about which side a flow
is on.

---

## 8. Metrics before and after — S3 rho = 0.90

| metric | before (`INVALID_…`) | after (`fixE`) |
|---|---|---|
| `max floor_wire` | 6.9160 G | **6.8120 G** |
| `DRAIN_MAX` at full floor | 0.9894 C | **0.3188 C** (single value) |
| `min sumR` | 0.1064 G | **10.0000 G** |
| queue peak | 1,177,952 B = **112.3 % of Q_abs** | 54,496 B = **5.20 %** |
| RED epochs | 198,721 | **0** |
| incast mean FCT | 59.6253 ms | **59.3909 ms** |
| background goodput | — | 7.3828 Gbps (acked 1.8457 GB, not complete at 3 s) |
| PFC events | — | **0** |
| retransmitted bytes | — | **0** |
| `scope_violations` | n/a | **0** |
| `ownership_transitions` | n/a | **1** |
| `path_metadata_missing` | n/a | **0** |

### rho = 0.9875 (run only after rho = 0.90 passed every gate)

`floor_payload = 6.5000 G`, `floor_wire = 6.8120 G`, `DRAIN_MAX = 3.1880 G`
(single value over 11,863 full-overlap epochs), `newGen = 64`, `oldSide = 1`.
Incast mean FCT 59.3404 ms, p99 59.3557 ms; background goodput 7.3830 Gbps;
queue peak 53,448 B = 5.10 % of Q_abs; RED 0; PFC 0.

### Verification sequence (in the required order)

| gate | result |
|---|---|
| `wire_accounting_audit.py` | **15/15** |
| `lifecycle_scope_test.py` | **30/30** |
| `three_set_test.py` | **26/26** |
| compile | **0 errors** |
| flag = 0 bit-identity | **21/21 files** hash-identical to `au_s3_rho090_out`, a baseline produced **before the controller code existed** |
| S3 rho = 0.90 | **27/27 gates** |
| S3 rho = 0.9875 | **27/27 gates** |

30-cell was not run. Nothing was committed or pushed.

### Failed-gate first counter-examples

Every gate failure encountered during this round, with its first counter-example
and its disposition. No failure was resolved by tuning.

| gate | first counter-example | cause | disposition |
|---|---|---|---|
| A-3/A-4 (round 1) | first owning epoch, `floor_wire = 6.7072 G` | defect C: floor summed over the steered set (64) | code fixed |
| B-1 (round 1) | `t = 2059410000`, `DRAIN_MAX = 10.0000 G`, `floor_wire = 0` | defect C: GC keyed on `live`, erasing the background entry the epoch it was created | code fixed (`fixE`) |
| C-3/C-5/B-4 (round 2) | `t = 2059410000`, 30 epochs, `floor_count = 1` | **gate mis-specification** — tested reported headroom, not emitted drain (`sum(drain) = 0`) | gate corrected |
| C-5 (rho = 0.9875) | `t = 2059325000`, single epoch, `floor_wire = 6.7072 G` with `floor_count = 64` | **gate mis-specification** — 6.7072 G is correct for 64 live members | gate corrected to `floor == count × MIN_RATE` |
| A3 / F1 / B7 (static) | comment text matched as if it were code | **test mis-specification** | tests corrected (strip comments; test semantics not literals) |

---

## 9. Files changed, diff summary, hashes

```
 simulation/scratch/third.cc                    |  109 +
 simulation/src/point-to-point/model/rdma-hw.cc |  706 +
 simulation/src/point-to-point/model/rdma-hw.h  |  225 +
 3 files changed, 1040 insertions(+)
```

Patch scripts (kept for provenance): `fixA_wire.py`, `fixB_scope.py`,
`fixC_floorscope.py`, `fixD_trace.py` (telemetry only), `fixE_gc.py`.

New analysis/test scripts under `simulation/experiment/scheme1_sba/`:
`wire_accounting_audit.py`, `lifecycle_scope_test.py`, `three_set_test.py`,
`scope_acceptance.py`, `report_extract.py`.

Trace `qc_trace.csv` gained 7 columns (31 total): `floor_count`,
`new_gen_count`, `old_side_count`, `ledger_count`, `ownership_transitions`,
`scope_violations`, `path_metadata_missing`.

### Frozen values — confirmed untouched

`Q_abs` / `Q_low` / `Q_high` / `Q_red` / `M_safe` (67,072 B), `H_guard` = 175 µs,
`MAX_BOOST` = 0.30 C, `rho`, `MIN_RATE` = 100 Mbps, the nonlinear migration
formula, the RED-band formula, ECN/PFC thresholds, pg = 3, `ShouldSendCN()`,
`CBAP_DELAY_CREDIT_ENABLE = 0`, controller flag default 0.

Asserted structurally by `three_set_test.py`: no literal `0.30`, `175`,
`838.86` or `67072` appears in the controller code; no hardcoded `65`, `64`,
`6812000000` or `3188000000` anywhere in the fix; no global `sumR <= C` clamp
was reintroduced (short-term `sumR > C` at low queue remains permitted).

### Results retained, not deleted

- `qc_s3_rho090_out.INVALID_WIRE_ACCOUNTING_AND_CONTROL_SCOPE/` — provenance
- `qc_s3_rho090_fix_out/` — defect A+B only, floor 6.7072 G (superseded)
- `qc_s3_rho090_fixC_out/` — three sets correct, GC bug present (superseded)
- `qc_s3_rho090_fixE_out/`, `qc_s3_rho09875_fixE_out/` — **current, 27/27**
- `flag0_new_out/`, `flag0_c_out/`, `flag0_e_out/` — bit-identity evidence
