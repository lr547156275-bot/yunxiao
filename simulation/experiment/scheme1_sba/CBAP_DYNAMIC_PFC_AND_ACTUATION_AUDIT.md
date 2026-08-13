# CBAP-SBA — Dynamic PFC and Actuation Audit

Audit-only round. **No queue controller was implemented.** The purpose is to
establish, from source and from traces, the facts the three-zone controller would
depend on — and to reject the ECN-threshold proxy for PFC that was proposed in the
previous round.

Scope guards honoured: nothing was reset or reverted; the pg=3 correction, the
analysis-script fixes and the stale-invariant correctness fix are all retained;
`MIN_RATE` was not modified; 50:50 was not restored; no queue-credit or rate-lease
code was written; no 30-cell matrix; nothing pushed.

Branch `cbap-queue-delay-credit`, HEAD `95160dc` (uncommitted working tree).

| Artifact | sha256 (first 16) |
|---|---|
| `build/scratch/third` | `91491eac84ca4036` *(4-stage actuation trace)* |
| `build/libns3.18-point-to-point-debug.so` | `6279fd24b1900364` |

### Scoped diff — the audit changes touch trace/hook paths only

`git diff` against the pg=3 baseline reports 1,527 added / 1,114 removed lines for
`third.cc`, which is **misleading**: `git diff --ignore-all-space` gives
**413 / 0**. The 1,114 "removals" are CRLF/whitespace artifacts, not edits. A
diff against a snapshot taken immediately before any audit edit
(`third.cc.bak_preaudit`) is the honest measure:

| Metric | Value |
|---|---|
| lines added | **332** |
| lines removed | **0** |
| added lines matching `m_rate`/`ChangeRate`/`m_nextAvail`/`MinRate`/`RateAI`/`targetRate`/`migration`/`Replan`/`mlx.`/`hp.`/`dctcp`/`tmly` | **1 — and it is a comment** stating the code does not touch them |
| identifiers introduced | all `cbap_actuation_*`, `cbap_pfc_*`, `CbapActuation*`, `SampleCbapPfcAudit`, `GetCbapQpForAudit` |

`rdma-hw.cc`, filtered to rate-affecting writes:

| Check | Result |
|---|---|
| added lines writing `m_rate` / `ChangeRate(` / `m_nextAvail` / `mlx.m_targetRate` / `hp.m_curRate` / `appliedRateBps` / `migrationTargetBps` | **none** |
| removed lines writing any of those | **none** |
| total audit additions | 4 lines: a `NULL`-initialised hook pointer, the read-only `GetCbapQpForAudit` accessor, and a 2-line `if (hook) hook(...)` call after the pre-existing `ChangeRate` |

`rdma-hw.h`: 3 added lines (hook declaration + accessor declaration + comment).

**`switch-mmu.cc`, `switch-mmu.h` and `switch-node.cc` are not modified at all**
(`git diff --stat` returns empty), so `ShouldSendCN()`, the ECN marking logic, the
PFC predicate and the dynamic PFC threshold are provably untouched.

The hook pointer defaults to `NULL` and is installed only when a scenario supplies
a trace filename, so a run without the trace keys is bit-identical to before.

New config keys, each verified parsed exactly once with zero collisions:
`CBAP_PFC_AUDIT_FILE`, `CBAP_PFC_PORTS_FILE`, `CBAP_ACTUATION_FILE`.

---

## 1. Exact PFC trigger semantics

The pause decision is `SwitchMmu::CheckShouldPause` (`switch-mmu.cc:77`):

```cpp
!paused[port][qIndex]
  && ( hdrm_bytes[port][qIndex] > 0
       || GetSharedUsed(port, qIndex) >= GetPfcThreshold(port) )
```

Resume is `CheckShouldResume` (`:80`), requiring `hdrm_bytes == 0` **and**
`shared_used + resume_offset <= threshold`, with `resume_offset = 3072 B`.

Supporting definitions:

| Quantity | Definition | Value in S3 |
|---|---|---|
| `GetSharedUsed(port,q)` | `max(0, ingress_bytes[port][q] − reserve)` | `reserve = 4096 B` |
| `GetPfcThreshold(port)` | `(buffer_size − total_hdrm − total_rsrv − shared_used_bytes) >> pfc_a_shift[port]` | **bytes** |
| `buffer_size` | `BUFFER_SIZE 8` → 8 MiB | 8,388,608 B |
| `total_hdrm` | Σ per-port `headroom = rate·delay/8/1e9·3` | 45,000 B |
| `total_rsrv` | `n_port × reserve` | 32,768 B |
| `pfc_a_shift` | `shift = 3` (`third.cc:3825`) | ÷8 |

Switch 84 has **8 ports** (hosts 64–67 at 1 µs → headroom 3,750 B each; uplinks to
85–88 at 2 µs → 7,500 B each), so the 64-way incast arrives over **4 uplink
ingress ports**, not 64. Threshold at `shared_used_bytes = 0`:

```
(8388608 − 45000 − 32768) >> 3 = 1,038,855 B  ≈ 831.08 µs of 10 G
```

The threshold **shrinks as the shared pool fills** (`USE_DYNAMIC_PFC_THRESHOLD 1`),
so it is not a constant and cannot be pre-computed into a fixed delay bound.

## 2. `queue_bytes` and the PFC counter are NOT the same quantity

This is the decisive finding, and it rejects the 400 KB ECN proxy.

`switch-node.cc:190-195`:

```cpp
m_mmu->UpdateIngressAdmission(inDev, qIndex, p->GetSize());   // INGRESS port
m_mmu->UpdateEgressAdmission(idx,   qIndex, p->GetSize());    // EGRESS port
CheckAndSendPfc(inDev, qIndex);                               // <-- INGRESS
```

- **PFC** is evaluated on `inDev`, the **ingress** port, over `ingress_bytes[][]`,
  a shared-buffer accounting counter.
- **CBAP** samples `sw->GetEgressQueueBytes(ifIndex)` (`third.cc:838`) — the
  **egress** `BEgressQueue` of the bottleneck port.

Different ports, different data structures, different semantics. Measured ratio
over the batch window at rho=0.9875:

```
mean( pfc_counter_occupancy / cbap_egress_queue_bytes ) = 0.2823   (11,363 samples)
```

Not 1.0, and not constant across rho. **Conclusion: they must not be subtracted,
converted, or collapsed into a single queue-delay threshold.** Two independent
guards are required, exactly as specified. No `pfc_safe_delay` is derived, and the
`ecnThresholdBytes = 400,000 B` proxy is **not used**.

### Measured dynamic threshold during the batch (t ∈ [2.000, 2.090] s, 18,001 samples/cell)

| rho | thresh min / mean / max (B) | in µs | PFC occ max | slack min (B) | CBAP egress q max | shared_used max | guard state |
|---|---|---|---|---|---|---|---|
| 0.55 | 1,034,341 / 1,037,036 / 1,038,855 | 827.5 / 829.6 / 831.1 | 15,816 B (12.65 µs) | 1,020,788 | 56,592 B (45.27 µs) | 36,112 B | SAFE ×18001 |
| 0.75 | 1,029,756 / 1,034,495 / 1,038,855 | 823.8 / 827.6 / 831.1 | 22,104 B (17.68 µs) | 1,007,652 | 93,272 B (74.62 µs) | 72,792 B | SAFE ×18001 |
| 0.90 | 1,033,829 / 1,037,863 / 1,038,855 | 827.1 / 830.3 / 831.1 | 13,720 B (10.98 µs) | 1,020,109 | 56,592 B (45.27 µs) | 40,208 B | SAFE ×18001 |
| 0.9875 | 1,002,651 / 1,027,570 / 1,038,855 | 802.1 / 822.1 / 831.1 | 93,368 B (74.69 µs) | 909,283 | **309,160 B (247.33 µs)** | 289,632 B | SAFE ×18001 |

`pfc_guard_state` was `SAFE` in **100 %** of samples in all four cells — no
TRIGGER, no NEAR, no PAUSED. PFC never came close: worst-case slack was
909,283 B. **The application delay guard binds far earlier than the PFC guard in
this scenario**, which means the PFC guard is a genuine backstop here rather than
the active constraint. It must still be implemented exactly (not proxied),
because that ordering is a property of S3's parameters, not a law.

New trace columns emitted (`pfc_audit.csv`, 600,000 rows/cell):
`time_ns, link_id, cbap_egress_queue_bytes, egress_port_occupancy_bytes,
worst_ingress_port, pfc_counter_occupancy_bytes, dynamic_pfc_threshold_bytes,
pfc_slack_bytes, hdrm_bytes, shared_used_bytes, total_hdrm, total_rsrv,
sum_ingress_bytes, pfc_guard_state`.

`pfc_guard_state` mirrors `CheckShouldPause` term for term.

### Per-ingress-port detail — all ports that actually feed the bottleneck egress

The PFC predicate is per ingress port, so a single aggregate figure would hide
which port is closest to pausing. A port counts as a **contributor** only if its
observed `rx_bytes` is non-zero — decided by measurement, not assumed from the
topology, so a port that never carries data cannot depress the reported minimum.

Measured: exactly **5 contributing ports** on switch 84 — **if 2** (the locally
attached background source, host 65) and **if 5–8** (the four uplinks to 85–88
carrying the 64 incast senders on hosts 0–63). The egress under control is if 1.
Window t ∈ [2.000, 2.090] s, 89,989 rows per cell.

| rho | port | occ max (B) | thresh min (B) | **slack min (B)** | hdrm max | paused |
|---|---|---|---|---|---|---|
| **0.55** | 2 | 15,816 | 1,034,341 | 1,020,788 | 0 | 0 |
| | 5 | 9,528 | 1,034,341 | 1,025,206 | 0 | 0 |
| | 6 | 6,384 | 1,034,341 | 1,028,350 | 0 | 0 |
| | 7 | 11,624 | 1,034,341 | 1,022,717 | 0 | 0 |
| | 8 | 8,480 | 1,034,341 | 1,026,254 | 0 | 0 |
| | | | | **min = 1,020,788 (816.63 µs)** | | |
| **0.75** | 2 | 14,768 | 1,029,756 | 1,014,988 | 0 | 0 |
| | 5 | 15,816 | 1,029,756 | 1,013,940 | 0 | 0 |
| | 6 | 10,576 | 1,029,756 | 1,019,966 | 0 | 0 |
| | 7 | 22,104 | 1,029,756 | 1,007,652 | 0 | 0 |
| | 8 | 13,720 | 1,029,756 | 1,016,036 | 0 | 0 |
| | | | | **min = 1,007,652 (806.12 µs)** | | |
| **0.90** | 2 | 4,288 | 1,033,829 | 1,032,018 | 0 | 0 |
| | 5 | 11,624 | 1,033,829 | 1,022,205 | 0 | 0 |
| | 6 | 8,480 | 1,033,829 | 1,025,480 | 0 | 0 |
| | 7 | 13,720 | 1,033,829 | 1,020,109 | 0 | 0 |
| | 8 | 10,576 | 1,033,829 | 1,023,384 | 0 | 0 |
| | | | | **min = 1,020,109 (816.09 µs)** | | |
| **0.9875** | 2 | 1,144 | 1,002,651 | 1,002,651 | 0 | 0 |
| | 5 | **73,456** | 1,002,651 | 929,195 | 0 | 0 |
| | 6 | **57,736** | 1,002,651 | 944,915 | 0 | 0 |
| | 7 | **93,368** | 1,002,651 | **909,283** | 0 | 0 |
| | 8 | **68,216** | 1,002,651 | 934,435 | 0 | 0 |
| | | | | **min = 909,283 (727.43 µs)** | | |

`headroom_bytes = 0` and `paused = 0` on every contributing port in every cell, so
**neither term of `CheckShouldPause` was ever satisfied**.

The rho=0.9875 row is the informative one: pressure moves off the local port
(if 2 drops to 1,144 B, because the background flow is squeezed to its floor) and
concentrates on the four **uplinks** (57,736–93,368 B), which is where the 64
incast senders arrive. Minimum slack still leaves 909,283 B of margin — PFC was
never close. Trace: `pfc_ports.csv`, columns
`time_ns, link_id, ingress_port, ingress_bytes, shared_used_bytes,
dynamic_pfc_threshold_bytes, pfc_slack_bytes, headroom_bytes, paused,
egress_bytes, rx_bytes_total`.

## 3. Full closed-loop H_eff — directly measured in four stages

**This supersedes the earlier "≈20 µs" estimate in §3a.** That figure added two
separately-measured legs (5.0 µs + 15.0 µs) and was side-evidence, not a closed-loop
measurement. The four-stage instrumentation below measures the loop directly, and
the answer is materially larger.

### Correlation method

`flowId` alone cannot establish causality between stages, so each rate command is
assigned a monotonically increasing `command_generation` and correlated by
**(stable QP key, generation, packet sequence)**:

| Stage | Event | Key recorded |
|---|---|---|
| 1 `rate_command` | new pacing rate installed (after the pre-existing `ChangeRate`) | generation; QP 5-tuple `(sip, dip, sport, dport, pg)` |
| 2 `sender_rate_effect` | first packet this QP schedules under the new rate | `seq = qp->snd_nxt` at dequeue |
| 3a `arrival_at_bottleneck` | that `(key, seq)` **joins** the bottleneck egress queue | matched back to generation |
| 3 `first_affected_at_bottleneck` | that `(key, seq)` **leaves** the egress queue | matched back to generation |

### Gates (S3, rho = 0.90) — all pass

| Gate | Result |
|---|---|
| `rate_command > 0` | **569** |
| `sender_rate_effect > 0` | **152** |
| `arrival_at_bottleneck > 0` | **152** |
| `first_affected_at_bottleneck > 0` | **152** |
| generations with all four stages | **152** |
| stage-2 generations missing stage 1 | **0** |
| stage-3a generations missing stage 2 | **0** |
| stage-3 generations missing stage 3a | **0** |
| ordering violations `t1 ≤ t2 ≤ t3a ≤ t3` | **0** |
| `unmatched` | **0** |
| `negative` | **0** |
| `inflight` at end of run | **0** |

Counters are emitted by the run itself as trailing CSV rows
(`counters_unmatched_0_superseded_359_negative_0`,
`counters_pending_58_inflight_0`), so the gate values live with the data rather
than depending on post-hoc analysis.

### Why 417 of 569 commands have no stage 2 — and a counter defect I fixed

**359 (86.1 %)** were **superseded**: a later command for the same QP arrived
before any packet departed under the earlier one. With a 5 µs control epoch and 65
flows this is expected, not a fault. The remaining **58** were each flow's final
command, with no further send — these are the `pending` count at end of run.
All 65 flows appear in both stage 1 and stage 2, so no flow is systematically
missed.

**Counter defect:** an earlier version reported `duplicate = 0`, which was
vacuous — it counted duplicate *generations*, and generation is a monotonic
`++` counter, so duplicates are impossible by construction. The quantity that
matters is displaced *pending entries*, i.e. supersession. Now counted correctly
and reported as `superseded = 359`.

### Measured components (S3, rho = 0.90; µs; 152 four-stage triples)

| Component | n | min | mean | p50 | p95 | p99 | max | meaning |
|---|---|---|---|---|---|---|---|---|
| `H_obs` | 152 | 5.000 | 5.000 | 5.000 | 5.000 | 5.000 | 5.000 | telemetry sample → controller sees it |
| `H_sender` | 152 | 0.000 | 23.710 | 7.920 | 46.751 | 46.751 | 67.756 | rate command → sender effect |
| `H_path` | 152 | 2.895 | 60.087 | 67.138 | 75.995 | 82.918 | 84.998 | sender → bottleneck **arrival** |
| `H_egressq` | 152 | 0.000 | 26.269 | 26.900 | 44.968 | 45.336 | 45.336 | arrival → dequeue (egress queueing) |
| **`H_eff` (arrival)** | 152 | **8.034** | **88.797** | **86.762** | **125.232** | **128.584** | **157.754** | **use this** |
| `H_eff` (dequeue) | 152 | 8.034 | 115.066 | 124.948 | 168.524 | 172.714 | 174.390 | double-counts the queue |

### Cross-rho H_eff(arrival) — 5 cells, and the H_guard it sets

| Cell | n | min | mean | p50 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|
| S3 rho=0.55 | 29 | 8.014 | 10.984 | 9.910 | 16.340 | 18.179 | 18.179 |
| S3 rho=0.75 | 27 | 8.171 | 11.896 | 10.999 | 19.013 | 31.838 | 31.838 |
| S3 rho=0.90 | 152 | 8.034 | 88.797 | 86.762 | 125.232 | 128.584 | 157.754 |
| S3 rho=0.9875 | 82 | 8.034 | 77.802 | 89.708 | 98.088 | 100.602 | 170.328 |
| S4 rho=0.90 | 153 | 7.955 | 86.928 | 81.767 | 126.001 | 129.353 | 169.159 |
| **GLOBAL** | **443** | **7.955** | **76.335** | **84.248** | **125.163** | **129.422** | **170.328** |

(µs; arrival variant; four-stage-complete generations only)

```
H_guard = ceil(global_max / 5 µs) × 5 µs
        = ceil(170.328 / 5) × 5 = 175.0 µs   (35 control epochs)
```

**`H_guard` = 175 µs**, not the 160 µs candidate — the measured global max is
170.328 µs (S3 rho=0.9875), which rounds up to 175 µs. Worst case by construction:
mean and p95 are deliberately not used, because a tail of actions would otherwise
land after the guard window had closed.

Stage completeness per cell (no unmatched, no negative, zero inflight at end):

| Cell | cmd | sender | arrival | dequeue | full |
|---|---|---|---|---|---|
| S3 rho=0.55 | 249 | 29 | 29 | 29 | 29 |
| S3 rho=0.75 | 270 | 27 | 27 | 27 | 27 |
| S3 rho=0.90 | 569 | 152 | 152 | 152 | 152 |
| S3 rho=0.9875 | 323 | 82 | 82 | 82 | 82 |
| S4 rho=0.90 | 667 | 153 | 153 | 153 | 153 |

`sender = arrival = dequeue = full` in every cell, so every observed sender effect
was tracked all the way to the bottleneck.

**A strong rho dependence, worth noting:** H_eff at rho ≤ 0.75 is an order of
magnitude smaller (max 18–32 µs) than at rho ≥ 0.90 (max 158–170 µs). At low rho
the batch runs at/near `MIN_RATE` with little queueing, so commands take effect
almost immediately; at high rho the sender is paced faster, the queue is deeper,
and both `H_sender` and `H_path` grow. A single `H_guard` must cover the worst
case, hence 175 µs — but the controller will be conservative by ~10× at low rho.
That is the correct trade for a safety guard and is recorded rather than tuned.

### Which H_eff the controller must use, and why

**`H_eff` (arrival) — p50 ≈ 86.8 µs, p95 ≈ 125.2 µs.**

`EgressDequeue` fires when a packet *leaves* the egress queue, so the dequeue
variant includes `H_egressq` — the queueing delay at the very bottleneck the
predictor is trying to estimate. Using it would **double-count the queue**:
`predicted_delay = queue_delay + (A−C)·H/C` already contains the current queue in
its first term, so an `H` that also contains it inflates the prediction and would
trip the guards early. The arrival variant ends where the packet joins the queue,
which is the correct boundary.

`H_egressq` (mean 26.3 µs, max 45.3 µs) is independently useful: it matches the
observed egress queue peak of 56,592 B = 45.27 µs at rho = 0.90, an internal
consistency check across two unrelated measurements.

### Consequence: pending actions, NOT stale feedback

An earlier draft of this section described the situation as "recomputing against
stale feedback for ~17 epochs". **That was the wrong characterisation and is
withdrawn.** The queue observation `Q(t)` is *not* stale: it is delivered 5.0 µs
after sampling (`H_obs`, measured constant) and accurately describes the queue as
it was 5 µs ago.

The actual problem is different and more specific: at any instant there are
approximately `H_eff / 5 µs` **pending actions** — rate commands already issued
whose effect has not yet reached the bottleneck, and which are therefore **not yet
visible in `Q(t)`**. `Q(t)` is correct about the past; it simply cannot contain
what has not arrived.

This forces a four-state accounting per flow:

| State | Meaning | Visible in `Q(t)`? |
|---|---|---|
| `desired` | what the controller wants this epoch | no |
| `commanded` | written to the QP (stage 1 fired) | no |
| `effective` | the sender is actually pacing at it (stage 2 fired) | not yet |
| `pending` | commanded but not yet effective, or effective but not yet arrived | **no — must be added explicitly** |

`R_effective` is the only rate that describes bytes actually entering the network.
Substituting the most recent `commanded` rate for it would assert an effect that
has not happened; ignoring the pending set would under-predict the queue by
exactly the in-flight excess. Both errors are forbidden in the contract below.

### Measured pending-action ledger — and a correction to my own projection

Measured per 5 µs epoch across all five cells (`pending_ledger.py`):

| Cell | epochs with ≥1 pending | pending count (non-zero epochs) p50 / p95 / max | pending **excess** max | as queue delay | superseded |
|---|---|---|---|---|---|
| S3 rho=0.55 | 31 / 17,592 (0.2 %) | 1 / 3 / **3** | 1,765 B | **1.41 µs** | 162 |
| S3 rho=0.75 | 33 / 14,084 (0.2 %) | 1 / 2 / **2** | 0 B | 0.00 µs | 181 |
| S3 rho=0.90 | 77 / 11,387 (0.7 %) | 10 / 66 / **129** | 859 B | 0.69 µs | 359 |
| S3 rho=0.9875 | 75 / 11,376 (0.7 %) | 1 / 66 / **66** | 374 B | 0.30 µs | 180 |
| S4 rho=0.90 | 77 / 11,380 (0.7 %) | 2 / 66 / **130** | 799 B | 0.64 µs | 451 |

**Correction.** An earlier draft projected that pending actions would put
"54,250 B = 43.4 µs" of invisible queue in flight, by assuming `A = 1.5 C`
sustained across the horizon. **The measurement does not support that**, and the
projection is withdrawn. Measured pending excess peaks at **1,765 B = 1.41 µs** —
roughly 30× smaller. The reason is visible in the trace: in these cells the rate
commands are predominantly *decreases* (the background flow being walked down by
migration), so `max(0, R_commanded − R_effective)` is near zero. The pending set is
large in **count** (up to 130 simultaneous) but negligible in **committed excess**.

Two consequences, and they pull in opposite directions:

- `pending_excess_bytes` is **not** currently a large term, so it is not the
  dominant risk in these cells. It must still be in `Q_pred` — with a controller
  issuing positive `boost`, the sign flips and the term becomes exactly the
  quantity that was missing when the queue-credit attempt diverged. Its smallness
  here is a property of a *boost-free* workload, not of the mechanism.
- The **count** being up to 130 does justify the single-outstanding-boost rule: a
  boost cannot be re-evaluated before its own effect lands, and 130 concurrent
  unconfirmed actions is exactly the regime where stacking becomes untrackable.

Also note actuation is extremely bursty — active in only **0.2–0.7 %** of epochs.
Percentiles over the whole run are therefore meaningless (p95 reads 0.0 while the
max is 130); the table above reports non-zero epochs separately for that reason.

`H_sender` has a wide spread (p50 7.9 µs, max 67.8 µs) because a paced flow may be
mid-gap when the command lands, so a single scalar horizon understates the tail.

**No value was hardcoded**: every figure above is derived from the trace.

---

## 3a. Earlier two-leg estimate (superseded, retained for provenance)

The 5 µs figure from the previous round was only the **first leg**, as you noted.
Measured legs:

| Leg | Measured | Evidence |
|---|---|---|
| `queue_sample_time` → control observes | **5.0 µs** | `port_summary`: `sample=999995000 → delivery=1000000000`, constant over all rows; equals one `CBAP_CONTROL_EPOCH_US 5` |
| release → first affected packet at bottleneck | **15.0 µs** | release `2.000005 s`; queue steps 0 → 33,536 B at `2.000020 s`. Identical for all four rho |
| rate command → observable rate change | **95.0 µs** (rho ≥ 0.90) | rate holds 143.7500 through `2.000080`, moves to 148.2956 at `2.000100` |

```
H_eff = first_affected_packet_at_bottleneck_time − queue_sample_time
      ≈ 15.0 µs + 5.0 µs = 20.0 µs
```

This matches the ~20 µs the specification anticipated, and it is **derived from
trace, not hardcoded**. The 15.0 µs leg is essentially the base RTT (15.2 µs of
one-way propagation plus serialization) and is physically irreducible.

### Structural first-burst / in-flight bytes

The specification requires the synchronous first-packet burst to be counted. Measured:

```
t=2.000020  q =  33,536 B = 32.0 × 1048 B
t=2.000030  q =  54,496 B = 52.0 × 1048 B
```

So the burst arrives as a ramp, not all 64 at once: 32 packets land in the first
10 µs sample, 52 by the next. The full structural bound is
`64 × 1048 = 67,072 B = 53.66 µs`, and the observed peak stays below it at low rho.
A predicted-delay calculation over a 20 µs horizon must therefore include an
in-flight term of up to ~52 packets, not merely `(A−C)·H/C`.

### Caveat, stated rather than glossed

`rate_command_time` and `sender_rate_effect_time` have **no dedicated timestamps**
in the current source. The 95 µs figure above is inferred from the first change in
the sampled applied rate, so it is an **upper bound at 20 µs sampling
granularity**, not an exact instrument reading. The 5.0 µs and 15.0 µs legs are
directly measured. If the controller needs `H_eff` to better than one sample
period, dedicated timestamps must be added first; for a 20 µs horizon at 5 µs
epochs the present accuracy is adequate.

## 4. rho feasible interval — **scenario-specific**, computed for S3 and S4

```
rho_min = max(0, (N·R_min − (C − R_old_entry)) / R_old_entry)
rho_max = min(1, 1 − Σ old_min_rate / R_old_entry)
```

**These bounds depend on `R_old_entry`, so they are NOT transferable between
scenarios.** Every rho table in this report that is not explicitly labelled S4
applies to **S3 only**.

| Scenario | `R_old_entry` | `rho_min` | `rho_max` |
|---|---|---|---|
| **S3** (bg cap 8.0 G) | 8.0 G | **0.5500000** | **0.9875000** |
| **S4** (bg cap 9.5 G) | 9.5 G | **0.6210526** | **0.9894737** |

Both S3 values MATCH the specified 0.55 / 0.9875; both S4 values MATCH the
specified 0.6210526 / 0.9894737. Derivations:

```
S3: rho_min = (6.4 − 2.0)/8.0 = 0.5500000    rho_max = 1 − 0.1/8.0 = 0.9875000
S4: rho_min = (6.4 − 0.5)/9.5 = 0.6210526    rho_max = 1 − 0.1/9.5 = 0.9894737
```

### S3 test points (measured, this round)

| rho | R_old_base | R_new_base | per-flow | R_old ≥ R_min? |
|---|---|---|---|---|
| 0.55 | 3.600 G | 6.400 G | 100.0000 Mbps | yes |
| 0.75 | 2.000 G | 8.000 G | 125.0000 Mbps | yes |
| 0.90 | 0.800 G | 9.200 G | 143.7500 Mbps | yes |
| 0.9875 | 0.100 G | 9.900 G | 154.6875 Mbps | yes (= R_min) |

Tested points are 0.55 / 0.75 / 0.90 / **0.9875** — 0.99 was *not* tested, so
nothing was silently clamped.

### S4 equivalents (computed, not run this round)

| rho | R_old_base | R_new_base | per-flow | note |
|---|---|---|---|---|
| 0.6210526 (`rho_min`) | 3.600 G | 6.400 G | 100.0000 Mbps | floor case |
| 0.75 | 2.375 G | 7.625 G | 119.1406 Mbps | ≠ S3's 125.0000 |
| 0.90 | 0.950 G | 9.050 G | 141.4062 Mbps | ≠ S3's 143.7500 |
| 0.9894737 (`rho_max`) | 0.100 G | 9.900 G | 154.6875 Mbps | = R_min exactly |

Note that the *same* nominal rho yields **different** per-flow rates in S3 and S4
(0.75 → 125.0000 vs 119.1406 Mbps), which is another reason the S3 table must not
be reused for S4.

### The previous round's S4 cell is relabelled

| Field | Value |
|---|---|
| cell | `cr_s4_rho040` (previous round) |
| **`requested_rho`** | **0.40** |
| **`effective_rho`** | **0.6210526** |
| Substitution | silent clamp by `eta_feasible` = 0.6211 = S4's `rho_min` |
| Status | **must NOT be cited as a rho = 0.40 performance point** |

rho = 0.40 is **below S4's `rho_min` = 0.6210526**, i.e. an infeasible
configuration. It did not fail: `eta_feasible` came out as exactly `rho_min` and
clamped the request. So every number from that cell describes rho = `rho_min`,
not rho = 0.40. The 18/18 acceptance it passed remains valid *as a rho = rho_min
measurement* and is invalid as a rho = 0.40 one.

This is the behaviour now forbidden: an out-of-interval configuration must be
**reported as infeasible at preflight**, not clamped. `requested_rho` versus
`effective_rho` is emitted for every cell (§5), so this class of silent
substitution is detectable rather than invisible.

## 5. Measured first-batch DATA rate — requested == effective

| rho requested | grant per flow | effective rho | first applied rate (flow 1) | clamped? |
|---|---|---|---|---|
| 0.5500 | 100.0000 Mbps | **0.550000** | 100.0000 Mbps | no |
| 0.7500 | 125.0000 Mbps | **0.750000** | 125.0000 Mbps | no |
| 0.9000 | 143.7500 Mbps | **0.900000** | 143.7500 Mbps | no |
| 0.9875 | 154.6875 Mbps | **0.987500** | 154.6875 Mbps | no |

All 64 flows in each cell received an identical grant (single distinct value), and
the measured values equal the specification's 100.0000 / 125.0000 / 143.7500 /
154.6875 exactly. **Strictly monotone.** No `MIN_RATE` clamping occurred, because
every value is at or above the 100 Mbps floor.

### rho survives to first DATA (acceptance condition 1)

Trajectory of incast flow 1, 20 µs sampling, release at 2.000005 s:

| t (s) | phase | rho=0.55 | rho=0.75 | rho=0.90 | rho=0.9875 |
|---|---|---|---|---|---|
| 1.999980 | WAIT_RELEASE | 10000.0000 | 10000.0000 | 10000.0000 | 10000.0000 |
| 2.000000 | WAIT_RELEASE | **100.0000** | **125.0000** | **143.7500** | **154.6875** |
| 2.000020 | INJECTING | 100.0000 | 125.0000 | 143.7500 | 154.6875 |
| 2.000040 | INJECTING | 100.0000 | 125.0000 | 143.7500 | 154.6875 |
| 2.000060 | INJECTING | 100.0000 | 125.0000 | 143.7500 | 154.6875 |
| 2.000080 | INJECTING | 100.0000 | 125.0000 | 143.7500 | 154.6875 |
| 2.000100 | INJECTING | 100.0000 | 125.0000 | 148.2956 | 155.3109 |
| 2.000120 | INJECTING | 100.0000 | 125.0000 | 153.5671 | 155.3109 |

The rho-derived rate is held for **at least 4 epochs (80 µs)** across the
`WAIT_RELEASE → INJECTING` transition and through first DATA at the bottleneck
(15 µs). **rho is not overwritten before first DATA.**

At rho ≥ 0.90 the nonlinear migration then **visibly engages**
(143.75 → 148.2956 → 153.5671 → 154.5893), confirming the walk is observable once
the rate clears the `MIN_RATE` floor — and corroborating the corrected root cause
from the previous round (the walk was never broken; its output was simply below
the floor at rho < 0.55).

## 6. `pressure` currently comes from ECN — must be replaced

`rdma-hw.cc:2303-2304`:

```cpp
long double qMin = s_cbapConfig.budgetQLowFraction  * qEcn;   // 0.5
long double qMax = s_cbapConfig.budgetQHighFraction * qEcn;   // 1.0
long double u = qMax > qMin ? (q - qMin) / (qMax - qMin) : 1.0L;
```

with `qEcn = runtime.config.ecnThresholdBytes = 400,000 B` from
`s3_cbap_link.txt`. So the existing `migrationRiseSkew` pressure input **is
ECN-derived**, confirming the specification's suspicion. The three-zone controller
must replace this with the application-delay guard and the exact PFC guard;
`budgetQLowFraction` / `budgetQHighFraction` must not be silently reused for the
new semantics.

## 6a. Design contract for the controller: `m` versus `b`

Recorded here so the controller is built to a written contract rather than to
whatever the code happens to do. **Not implemented this round.**

The two mechanisms are distinct and must remain separately accounted:

| | **`m` — nonlinear migration** | **`b` — temporary queue boost** |
|---|---|---|
| Meaning | base capacity handover between old and new | short-lived permission to offer more than C |
| Sets | `R_old_target = R_old_base`, `R_new_base` | the excess: `sum(R_target) = C + b` |
| Driven by | `rho` (a configured allocation) | predicted queueing delay + PFC veto |
| Persistence | a trajectory that converges to base targets | **recomputed every epoch**, never accumulated |
| Conserves C? | yes — `R_old_base + R_new_base = C` | no, deliberately: `b > 0` fills the queue |

```
R_old_target  = R_old_base = (1 − rho) · R_old_entry
R_new_target  = R_new_base + boost − drain
sum(R_target) = C + boost − drain          with boost >= 0, drain >= 0
```

`boost` and `drain` are **separate non-negative terms**, not one signed variable.
Both are **recomputed from scratch every epoch**. Keeping them distinct means the
two directions are independently observable and independently bounded: a trace
showing `boost = 0, drain = 1.2 G` is unambiguous, whereas a single signed `b`
conflates "no boost granted" with "actively draining".

Neither term is a credit or a lease: they hold no balance between epochs and
expire by being recomputed, so there is nothing to expire, refresh, or reclaim.
That is the specific difference from the paused queue-credit direction, whose
failure mode was a persistent rate grant with no expiry
(`PERSISTENT_RATE_CREDIT_WITHOUT_LEASE_EXPIRY`).

Required behaviour, per epoch:

- `boost > 0` permitted only while predicted delay is below the soft bound **and**
  the exact dynamic PFC guard reports safe.
- `boost` **decays** as predicted delay approaches the hard bound — a graded
  reduction, not a step to any fixed target.
- When either hard bound is predicted to be crossed: `boost := 0` **and**
  `drain > 0`, so `sum(R_target) < C` and the queue actively empties. Slowing the
  increase is not sufficient — the queue would still diverge.
- Ordering: withdraw `boost` to 0 first, then raise `drain` using each flow's
  headroom above `MIN_RATE`. **Never below `MIN_RATE`.**
- Drain capacity is bounded by §7: total floor 6.5 G, so `drain <= 3.5 G` in S3.

### Zones

| Zone | Entry condition | `boost` | `drain` | Step function |
|---|---|---|---|---|
| **GREEN** | `Q_pred` below soft bound **and** PFC guard safe | may increase quickly | 0 | existing `migrationRiseBase` / `migrationRiseSkew` |
| **YELLOW** | `Q_pred` approaching a hard bound | non-linearly slowed, then withdrawn | 0 | reduced rise |
| **RED** | either hard bound predicted to be crossed, **or** PFC veto | **:= 0** | **> 0**, `sumR < C` | existing `migrationDecayBase` |

RED is not "increase more slowly" — that still diverges. It requires
`sumR < C` so the queue actively empties.

### Feature flag

The controller ships **behind a flag that is off by default**
(`CBAP_QUEUE_CONTROLLER_ENABLE 0`). With the flag off the code path must be
provably inert, verified the same way the queue-credit path was: an early return
plus a call gate, and a check that no state machine below the gate is reachable.
Existing cells therefore remain bit-identical.

Order of work, per instruction: state-machine unit tests and trace replay **first**;
only then the two S3 preflight cells (rho = 0.90 and 0.9875). No 30-cell matrix.

### Handoff continuity

At DCQCN handoff the initial rate must be **the flow's current actual applied
rate** — not `MIN_RATE`, not 100 Mbps, not the rate implied by any feasibility
ratio, and not the stock DCQCN initial rate. A CNP that has already arrived may
reduce the rate through normal DCQCN action, but the handoff itself must not
cause a feedback-free drop. Verification requires per-flow rate immediately
before and after handoff (`handoff_rate_before` / `handoff_rate_after`).

`m` continues to use the existing step functions (`migrationRiseBase = 0.30`,
`migrationRiseSkew = 0.35`, `migrationDecayBase = 0.30`); **no new coefficients**.

### Predicted queue — the exact expression the controller must use

```
Q_pred = max(0,
             Q_current
           + (R_effective − C) · H_guard / 8
           + pending_excess_bytes)
```

Units: `Q_current` and `pending_excess_bytes` in bytes, rates in bit/s, `H_guard`
in seconds, so `(R_effective − C) · H_guard / 8` is bytes.

Two prohibitions, both derived from the pending-action analysis in §3:

1. **`R_effective` must be the rate senders are actually pacing at** — the sum over
   flows whose stage-2 (`sender_rate_effect`) has fired for their latest command.
   Substituting the most recent `commanded` rate asserts an effect that has not
   happened yet, and would make `Q_pred` react to intentions rather than to bytes.
2. **`pending_excess_bytes` must not be dropped.** It is the in-flight excess
   already committed but not yet visible in `Q_current`:
   `Σ over pending generations of (R_commanded − R_effective) × (time since command)`,
   bounded by the horizon. Ignoring it under-predicts the queue by exactly the
   amount the controller itself has already put in motion — the failure mode that
   made the previous queue-credit attempt diverge.

`H_guard` is a **quantised worst case**, not an average:

```
H_guard = ceil(global_max(H_eff_arrival) / 5 µs) × 5 µs
```

Using the mean or p95 would leave a tail of actions whose effect arrives after the
guard window has closed. Quantising to the 5 µs control epoch keeps the horizon an
integer number of epochs, so the pending ledger has no partial-epoch remainder.

**Measured value: `H_guard` = 175 µs (35 epochs).** The 160 µs candidate was
slightly low — the cross-rho global max is 170.328 µs (§3), which rounds up to 175.

### Dual time scale

Observation and pressure evaluation run **every 5 µs** (one control epoch), but
positive boost is rate-limited by the actuation loop:

- **At most one unconfirmed positive `boost` generation per batch.** A new positive
  boost may only be issued after the outstanding one has either (a) been observed
  arriving at the bottleneck (stage 3a for its generation), or (b) timed out after
  `H_guard`.
- This exists because §3 shows a boost cannot be re-evaluated before its own effect
  lands. Issuing a second boost while the first is unobserved would stack
  committed excess that `Q_current` cannot yet show.
- **Preemption is always allowed** for RED entry, PFC veto, and `drain`. Safety
  actions are never rate-limited by the outstanding-boost rule; only *positive*
  boost is.
- `drain` may be issued every epoch.

### Pressure source — must change

Per instruction, the controller's **primary** pressure input is the bottleneck
**egress predicted queueing delay**:

```
predicted_delay = max(0, queue_delay + (aggregate_applied − C)·H_eff / C
                          + in_flight_burst_term)
queue_delay     = queue_bytes · 8 / C
H_eff           = H_eff(arrival)  -- measured, §3:  p50 86.8 us, p95 125.2 us
                  NOT the dequeue variant, which double-counts queue_delay
```

`H_eff` must be the **arrival** variant. The dequeue variant includes the egress
queueing delay that `queue_delay` already contributes, so using it double-counts
the queue and inflates the prediction.

The current ECN-derived pressure (`qEcn`, `qMin`, `qMax` — §6) **must not be used**
for this. The exact dynamic PFC guard (§1, §2) is an **independent safety veto**
only: it can force `b ≤ 0` but never sets the primary pressure, and its inputs are
never converted into a queue-delay figure.

ECN is **recorded only** — it is neither a hard bound nor required to be zero.

## 7. Drain feasibility — matches spec exactly

```
incast floor      = 64 × 100 Mbps = 6.4 G
background floor  =       100 Mbps = 0.1 G
total floor                        = 6.5 G      (spec: 6.5 G  MATCH)
drain headroom = C − total floor    = 3.5 G     (spec: 3.5 G  MATCH)
sum(min rates) < C                  = True
```

Active draining is therefore feasible: aggregate target can be pushed to 6.5 G,
i.e. 3.5 G below C. `MIN_RATE` was not modified.

## 8. Nonlinear migration call chain (gate from the previous round, re-confirmed)

```
RdmaHw::CbapEpochTick                          rdma-hw.cc:968
  ├─ ReplanCbapSbaMigrationTargets(now, why)   :2041   writes migrationTargetBps ONLY
  └─ EvaluateCbapSbaMigration(now)             :2282   writes the rate
        next = current + step·(target − current)        :2334
        step = migrationRiseBase·(1 + migrationRiseSkew·(1 − 2·pressure))   rise
        step = migrationDecayBase                                            decay
        appliedRate = max(minRate, floor(next))         :2341
```

A real per-epoch geometric walk exists, with `migrationRiseBase = 0.30`,
`migrationRiseSkew = 0.35`, `migrationDecayBase = 0.30`. **No alpha/gamma will be
invented**; the three zones will reuse these.

## 9. Outcome metrics, 4 rho + corrected HPCC (pg=3, same topology/traffic/seed)

| cell | BCT (ms) | FCT mean | FCT p99 | FCT max | max/min | queue peak (B) | queue delay (µs) | PFC | retx |
|---|---|---|---|---|---|---|---|---|---|
| rho=0.55 | 87.9173 | 87.8997 | 87.9168 | 87.9173 | 1.0004 | 56,592 | 45.27 | 0 | 0 |
| rho=0.75 | 70.3782 | 70.3610 | 70.3769 | 70.3782 | 1.0005 | 93,272 | 74.62 | 0 | 0 |
| rho=0.90 | 56.8939 | 56.8782 | 56.8934 | 56.8939 | 1.0006 | 56,592 | 45.27 | 0 | 0 |
| rho=0.9875 | **56.8354** | 56.8196 | 56.8349 | 56.8354 | 1.0006 | 309,160 | 247.33 | 0 | 0 |
| **HPCC** | 60.3267 | 59.7339 | 60.2272 | 60.3267 | 1.0332 | **1,296,010** | **1036.81** | 0 | 0 |

### CBAP vs corrected HPCC

| cell | BCT vs HPCC | queue peak vs HPCC |
|---|---|---|
| rho=0.55 | **+45.74 %** (worse) | 56,592 vs 1,296,010 B (**4.4 %**) |
| rho=0.75 | **+16.66 %** (worse) | 93,272 vs 1,296,010 B (7.2 %) |
| rho=0.90 | **−5.69 %** (better) | 56,592 vs 1,296,010 B (4.4 %) |
| rho=0.9875 | **−5.79 %** (better) | 309,160 vs 1,296,010 B (23.9 %) |

### Background protection

| cell | before (G) | during (G) | after (G) | service debt (Gb) |
|---|---|---|---|---|
| rho=0.55 | 7.6409 | 3.2685 | 7.5752 | 0.3844 |
| rho=0.75 | 7.6409 | 1.9173 | 7.5682 | 0.4028 |
| rho=0.90 | 7.6409 | 0.1004 | 7.5683 | 0.4290 |
| rho=0.9875 | 7.6409 | 0.0991 | 7.5680 | 0.4286 |
| HPCC | 7.3462 | 0.1532 | 7.3462 | 0.4339 |

At rho ≥ 0.90 the background flow is squeezed to its `R_min` floor (0.10 G) — by
construction, since `R_old_base = (1−rho)·8 G` = 0.8 G and 0.1 G respectively.
Background fully recovers after the batch in every cell (7.57 G vs 7.64 G before,
≈99 %).

### Reading of these numbers — what is and is not established

- **rho ≥ 0.90 beats corrected HPCC on BCT by ~5.7 %** while holding the
  bottleneck queue to 4–24 % of HPCC's. That is a real, measured result on one
  scenario and one seed.
- **It is bought by squeezing the background flow to its floor.** At rho=0.90 the
  background gets 0.1004 G during the batch versus HPCC's 0.1532 G — so CBAP is
  *not* protecting background better than HPCC at these operating points; it is
  slightly worse on that axis while better on BCT and much better on queue.
- rho=0.9875 gains only 0.06 ms over rho=0.90 (56.8354 vs 56.8939) but raises
  queue peak 5.5× (309,160 vs 56,592 B). The knob saturates well before its
  feasible maximum.
- **rho=0.99 as an "approaches HPCC" boundary hypothesis is not confirmed by
  equivalence** — at rho ≥ 0.90 CBAP already *exceeds* HPCC on BCT, so the
  hypothesis as posed (approaching from below) does not describe what was
  measured. No parameter was adjusted to narrow or widen any gap.
- HPCC's FCT spread is 1.0332 versus CBAP's ~1.0005: CBAP is markedly fairer
  across the 64 flows, which is the expected consequence of a single common grant.

## 10. Status of the three-zone controller: NOT implemented

Per section 7 of the instruction, implementation waits on this audit. Everything
the controller needs is now established:

| Input | Status |
|---|---|
| Exact PFC predicate + its counters | established (§1), read-only accessors all public |
| `queue_bytes` vs PFC counter same source? | **NO** (§2), ratio 0.2823 — two independent guards required |
| `H_eff` full closed loop | **directly measured in 4 stages** (§3): arrival variant p50 **86.8 µs**, p95 **125.2 µs**. The earlier ≈20 µs two-leg estimate is superseded |
| `app_hard_delay = msg·8/C` | 838.86 µs; `soft = 0.5 × hard` = 419.43 µs (**preflight value only**) |
| rho interval | 0.550000 … 0.987500 (§4) |
| Nonlinear step functions | exist and run (§8), reuse — no new coefficients |
| Drain headroom | 3.5 G (§7) |
| `pressure` source today | ECN-derived (§6), must be replaced |

Observed peak queue delay ranges 45.27 µs (rho=0.55/0.90) to 247.33 µs
(rho=0.9875) against `soft_delay` = 419.43 µs — so **all four measured cells sit
in the GREEN zone throughout**, and none of them exercises YELLOW or RED. A
controller validated only on these five cells could not demonstrate zone
transitions. Reaching YELLOW/RED requires either a positive `boost` (the
controller itself) or a scenario with more offered load; that should be decided
before the controller run, not after.

### Two findings that change controller design before a line is written

1. **The horizon is ~4× larger than the earlier estimate.** `H_eff` (arrival) is
   p50 86.8 µs / p95 125.2 µs = **17–25 control epochs** at 5 µs, not the ~4 epochs
   implied by 20 µs. "Recompute `boost`/`drain` every epoch" is still the right
   rule, but it must be understood as recomputing against feedback that is ~17
   epochs stale, not as closed-loop control at epoch granularity. Over an 86.8 µs
   horizon at `A = 1.5 C` the queue fills 54,250 B ≈ 43.4 µs — comparable to the
   whole observed queue peak — so a boost cannot be meaningfully re-evaluated
   before its own effect lands.
2. **`H_sender` variance is large** (p50 7.9 µs, max 67.8 µs), because a paced flow
   may be mid-gap when the command lands. A single scalar horizon understates this;
   the p95 figure is the safer input to a guard than the mean.

Neither finding was assumed — both come from the four-stage trace, and both argue
for conservative `boost` limits rather than for changing any frozen parameter.
