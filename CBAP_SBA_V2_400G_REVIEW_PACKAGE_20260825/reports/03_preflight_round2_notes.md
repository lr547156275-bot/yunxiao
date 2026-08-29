# v2_400g — Preflight round-2 notes (findings & dispositions from round 1)

Round-1 verdict was FAIL(7). Every failure traced to a measurement/model
artifact, not to a harness or simulator defect. Dispositions:

## 1. ns-quantization of per-packet tx time (single-flow "tx gap" FAILs)

ns-3 (this codebase) holds time in integer nanoseconds. A 1048B wire packet
takes 41.92ns at 200G and 20.96ns at 400G; truncation to 41/20ns skews the
effective per-packet rate by +2.2%/+4.8%. Measured gap medians were exactly
41.00/20.00ns — confirming truncation, not a rate bug.

**Disposition (config-only):** v2 uses `PACKET_PAYLOAD_SIZE 952` → wire
packet exactly 1000B → tx times 800/40/20ns exact at 10/200/400G. The
wire/payload ratio helpers derive from the configured size
(`CbapPayloadBytesPerPacket`), so all CBAP domain conversions follow
automatically. M_safe becomes FANIN×1000. v1 (10G, 1048B) is frozen and
unaffected.

## 2. Single-flow goodput 66–76% at 200/400G — criterion artifact, RETRACTED

Round 1 divided flow size by (last_ack − first_tx). That window includes the
trailing ACK RTT (~12µs), which is invisible at 10G (FCT 893µs) but 35% of
the whole FCT at 400G (22µs serialization). Recomputation: measured FCT
33.4µs = 21.97µs serialization + 12.08µs RTT — the sender ran at line rate
throughout (gap median = theory). **There is no window/BDP problem**; the
BDP window (604,000B at 400G) exceeds the payload-domain requirement
(~576KB).

**Disposition (analyzer-only):** goodput is now measured over the injection
window (first TX_BEGIN → last TX_BEGIN + 1 packet time) from the
serialization trace; the ACK tail becomes its own check (0.2–2 × RTT).
Probe size raised 1MiB → 8MiB so serialization dominates at every rate.

## 3. Burst q@1RTT −95% / −93% — single-link model wrong on a multi-tier fabric

The first-order theory ((N+bg−1)·C·RTT/8) predicts the *total* backlog, but
the topology is 89 nodes / 21 switches: in the first RTT the backlog forms
distributed across ToR/agg tiers, and the final bottleneck link sees only a
fraction. The simulator was right; the measurement point was wrong.

**Disposition (instrumentation + analyzer):** new observation-only keys
`QLEN_TS_FILE` / `QLEN_TS_INTERVAL_NS` emit an aggregate cross-switch queue
timeseries (sum + max port) from the existing `monitor_buffer` walk, default
OFF (byte-identical when unset — proven by twin regression regv3_b040 vs
scr8_b040). The burst check now compares the fabric-wide sum at rel+1RTT
against the same theory, ±30%.

## 4. heff_400g rc=143 — killed by codespace idle-stop, slowness claim RETRACTED

The cell was killed 11 minutes in by the platform's 30-minute idle shutdown
(02:51 HKT), at sim t=98.67ms of 132ms (75% done). Projected full runtime
~15 min. The earlier "pathologically slow at 400G" reading is retracted.

**Disposition (operational):** set the codespace idle timeout to 240 min
(GitHub → Settings → Codespaces) and/or keep the terminal attached while the
round-2 script runs.

## Carried-over measured values (round 1, still valid as measurements)

- H_eff (p99 of `first_affected_at_bottleneck`): **122.88µs @10G**,
  **14.84µs @200G**; 400G pending (cell re-runs in round 2).
  These are packet-1048 measurements; round 2 re-measures at packet-1000 and
  the round-2 values are the ones that feed screening.
- Round-1 raw results archived (moved, not deleted) to
  `results_r1_pkt1048/` with a pre-move manifest.
