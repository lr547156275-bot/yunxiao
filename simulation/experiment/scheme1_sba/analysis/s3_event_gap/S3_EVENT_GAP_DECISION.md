# S3 EVENT-LEVEL GAP DIAGNOSIS

**Verdict label: `CAUSAL_DIAGNOSIS_INCOMPLETE_TELEMETRY_GAP`**

Window W2 = [2.000000000, 2.058372997] s (58.372997 ms).  Binary
`e5020bbd2de2fa4b0add86323f985a70b95e7e680997226bc2e4f7487046c2c9`, seed 2,
same configs as the frozen reference apart from output paths and four telemetry
keys.

## 1. Telemetry bypass: all four gates passed

The tracers must not change what they measure.  Four independent byte-comparison
gates, run before any analysis:

| gate | comparison | result |
|---|---|---|
| 1a | CBAP telemetry-OFF vs frozen `sr_cbap_s3_out` | **16/16 identical, 0 differ** |
| 1b | DCQCN telemetry-OFF vs frozen `sr_dcqcn_s3_out` | **11/11 identical, 0 differ** |
| 2 | CBAP telemetry-ON vs telemetry-OFF, core results | **12/12 identical, 0 differ** |
| 3 | DCQCN telemetry-ON vs telemetry-OFF, core results | **12/12 identical, 0 differ** |

Turning the telemetry on changes no core result: `flow_summary`, `round_summary`,
`pfc_events`, `selected_link_timeseries`, `qc_trace`, `controller_summary`,
`flow_plan`, `qlen`, `feedback_summary`, `group_round_summary`,
`selected_flow_timeseries`, `tx_serialization` are all byte-identical.
**`FAIL_TELEMETRY_PERTURBATION` is NOT triggered.**

By construction the tracer contains no `Simulator::Schedule`, `Cancel` or
`Remove` -- only two `Simulator::Now()` calls, both read-only (asserted by unit
test on comment-stripped source).

## 2. Telemetry validation: 50/50 unit tests passed

Covering the four required cases plus structural integrity:

| case | result |
|---|---|
| duplicate attach | `Register()` returns -1, duplicate not stored (count stays 2) |
| missing link / unopenable trace | 6 `INVALID_CAUSAL_ATTACH` fail-fast guards, all `return 2` |
| empty trace | detected and reported, never read as "no events therefore no gaps" |
| multi-QP | pacer trace spans **65 distinct flows** (64 incast + 1 background) |
| header / column count | exact, 14 queue cols and 15 pacer cols |
| time monotone, within window | both arms |
| `ENQUEUE` delta == `packet_bytes` | **0 violations** (CBAP and DCQCN) |
| `DEQUEUE` delta == `packet_bytes` | **0 violations** (CBAP and DCQCN) |
| duplicate TX uid | none |
| cross-recorder agreement | causal(68800,68801) == txrec(68800,68801) |
| `new_next_avail >= candidate` | 0 violations |

Two initially-failing checks were resolved as measurement-boundary effects, each
proven rather than waived:

- **`TX_END` exceeds `TX_BEGIN` by one (DCQCN).**  The unmatched `TX_END` is row
  0 of the file, +752 ns after the window opened: its `TX_BEGIN` occurred before
  the trace window.  The **independent `tx_serialization.csv` recorder, a
  different hook, shows the identical asymmetry**, so this is a property of the
  window, not of either tracer.  No uid appears twice.  CBAP shows the symmetric
  pair: one orphan `END` at +425 ns and one orphan `BEGIN` 429 ns before close.
- **DCQCN pacer trace empty.**  The emit site sits inside `ChangeRate`'s CBAP
  branch (enclosing scope references `cbap.` and `CbapPacketGapNs`); DCQCN runs
  `CC_MODE 1, CBAP_ENABLE 0` and cannot reach it.  Expected by construction.
  **This must NOT be read as "DCQCN made no rate changes"** -- DCQCN's own rate
  path is not instrumented by this tracer.  It is a telemetry gap on the DCQCN
  side, and it is why the verdict label retains `TELEMETRY_GAP`.

## 3. The previous class-A finding is refuted by event-level data

The earlier classification used `selected_link_timeseries.csv`, sampled every
10,000 ns, to judge gaps whose p50 duration is 2,162 ns.  I had already
relabelled that result `A_ARTEFACT_STALE_QUEUE_SAMPLE` on timing-scale grounds.
The event-level trace now measures it directly:

| class | 10 us sample (previous) | **event-level (this round)** |
|---|---|---|
| queue non-empty, port idle | 971 gaps, **91.76 %** | **38 gaps, 1.26 %** |
| queue empty (arrival gap) | 83 gaps, 8.14 % | **1,027 gaps, 98.74 %** |

**91.76 % -> 1.26 %.**  About 97.7 % of the previous class A was a sampling
artefact.  The relabelling was correct, and the stop-gate correctly did not fire.

Between two consecutive queue events the depth is constant by construction, so
the occupancy profile over each gap is exact, not interpolated.  A gap counts as
"queue non-empty but idle" only if `q_bytes > 0` at **every** instant in it.

## 4. Event-level classification, five exclusive classes

| class | CBAP n | CBAP ns | share | DCQCN n | DCQCN ns | share |
|---|---|---|---|---|---|---|
| E `SIMULATION_END_CLIPPED` | 0 | 0 | 0 % | 0 | 0 | 0 % |
| A `QUEUE_NONEMPTY_PACER` | 38 | 31,550 | 1.26 % | 315 | 475,789 | 64.56 % |
| B `QUEUE_EMPTY_ARRIVAL` | **1,027** | **2,465,896** | **98.74 %** | 182 | 261,158 | 35.44 % |
| C `RATE_ACTUATION` | 0 | 0 | 0 % | 0 | 0 | 0 % |
| D `PROPAGATION_OR_UPSTREAM` | 0 | 0 | 0 % | 0 | 0 | 0 % |
| U `UNKNOWN` | **0** | **0** | **0 %** | **0** | **0** | **0 %** |
| total | 1,065 | 2,497,446 | | 497 | 736,947 | |

Percentiles:

| arm | class | p50 | p95 | p99 | max |
|---|---|---|---|---|---|
| CBAP | A | 572 | -- | 2,048 | 2,160 |
| CBAP | B | 2,162 | -- | 3,000 | 3,001 |
| DCQCN | A | 1,169 | -- | 4,042 | 4,292 |
| DCQCN | B | 1,173 | -- | 3,749 | 3,875 |

**Unexplained residual: 0 ns (0.00 %).**  All 1,065 CBAP and 497 DCQCN gaps fall
into a named class; nothing was folded into `UNKNOWN`.

## 5. Arm difference

| class | CBAP - DCQCN (ns) |
|---|---|
| A `QUEUE_NONEMPTY_PACER` | **-444,239** (CBAP has *less* of this) |
| B `QUEUE_EMPTY_ARRIVAL` | **+2,204,738** |
| total | **+1,760,499** (1.760499 ms) |

The total matches the independently computed idle excess from the byte deficit
(1.694845 ms from `8 x (3,420,068 - 1,301,512) / C`) to within 3.9 %, computed
from different data by a different route.

The gap excess is **entirely** in class B: CBAP idles with an *empty* bottleneck
queue 2.204738 ms more than DCQCN does, while actually suffering *less*
non-empty-queue idling.  The bottleneck was not failing to serve a backlog --
there was no backlog to serve.

## 6. Class C is zero, and that is a measurement, not an absence of telemetry

Independently witnessed from `actuation.csv`: **420 `rate_command` entries fall
in W2, and all 420 occur at or before t = 2,000,185,000 ns** -- the first 185 us,
0.32 % of the window.  Every one of them lies inside the pacer trace's span, so
`rate_commands_without_pacer_telemetry = 0` and `pacer_telemetry_complete = True`.

So over the remaining 58.19 ms, which contains 1,054 gaps totalling 2.494784 ms
(99.89 % of CBAP gap time), **CBAP issued no rate change at all**.  Those gaps
cannot be attributed to rate actuation because no actuation occurred there.

I withdraw a claim I made earlier this round: I first attributed the pacer
trace's 185 us span to redundant/dominated commands bypassing the emit site.
The witness data refutes that -- 420/420 commands are covered.  The trace is
complete; the window simply contains no later commands.

## 7. What is established and what is not

Established:

1. Telemetry is non-perturbing (4 gates, 39 files byte-identical) and validated
   (50/50 tests).
2. The previous 91.76 % class-A figure was a 10 us sampling artefact; the true
   event-level value is 1.26 %.
3. CBAP's excess idle time is **98.74 % queue-empty**, i.e. an arrival-side
   phenomenon at the bottleneck, not a service-side one.
4. The excess is not caused by rate actuation in the region where it occurs,
   because no rate commands occur there.
5. Gap durations remain quantised: CBAP class-B p50 = 2,162 ns, p99 = 3,000 ns,
   with `2,162 + 838 = 3,000` (838 ns = one 1048 B packet at 10 Gbps).

NOT established, and explicitly not claimed:

- **Which sender-side mechanism produces the 2,162/3,000 ns period.**  The
  bottleneck-side trace shows arrivals are late; it cannot show why.  Deciding
  this needs per-QP send-side event telemetry (`m_nextAvail` evaluation at every
  send opportunity, not only at rate changes), which does not exist in these
  outputs.
- **Whether closing these gaps would recover the 1.033590 ms tail component.**
  Magnitude sufficiency (1.760499 ms >= 1.033590 ms) is not causation.
- **Any statement about DCQCN's pacer decisions.**  DCQCN's rate path is not
  instrumented; its class-A/B split is measured, its cause is not.

Because item 6's decision requires knowing the sender-side mechanism, and the
sender-side pacer is only instrumented at rate-change instants -- of which there
are none in 99.7 % of the window -- the round's conclusion is:

**`CAUSAL_DIAGNOSIS_INCOMPLETE_TELEMETRY_GAP`**

"Not observed" is recorded as not observed.  No mechanism is declared absent, and
no controller, parameter, rho, `MAX_BOOST` or queue boundary change is proposed
or justified by this round.
