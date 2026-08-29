# -*- coding: utf-8 -*-
# Write the item 1-7 report files.  Read-only w.r.t. experiment data.
import hashlib
import os

D = '/work/simulation/experiment/scheme1_sba/analysis/s3_actuation_v2'
B = '/work/simulation/experiment/scheme1_sba'


def sha(p):
    if not os.path.exists(p):
        return 'ABSENT'
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 16), b''):
            h.update(c)
    return h.hexdigest()


PROV = """# ACTUATION PROVENANCE

## Item 2: rec2 vs ckpt4 -- NOT proven event-identical

| asset | rec2_s3_on_out | ckpt4_cbap_s3_out |
|---|---|---|
| binary sha256 | **265fe2a1a31d5e1809458c9e5b44120b528c2524ae2642cbd7185072a7b68103** | **290cb41fec981bc848cbfd518257ce2c5df1384d52f2325d67955acaabd880b7** |
| libns3 sha256 | c643f5cc332e02763946b01b8aa1cc17c50daf4dda53a371c13e4576525eb122 | c643f5cc332e02763946b01b8aa1cc17c50daf4dda53a371c13e4576525eb122 |
| third.cc sha256 | 84349f041424506b913072796bf2b224d59c4d82e6db679069c12dbd2f6802cd (at that build) | %s |
| recorder-ml header | 4b9a4098a6d31625e46d24cfd371956cfb1a3bb9c98bbc327a7de332c0ce4b10 | 4b9a4098a6d31625e46d24cfd371956cfb1a3bb9c98bbc327a7de332c0ce4b10 |
| config sha256 | %s | %s |
| topology / flow / link / path | 6091d5ec / 6b922c67 / 70903775 / 1557487d (identical) | same |
| SIM_SEED | 2 | 2 |

**The binaries differ.**  `290cb41f` adds the `CBAP_REALLOC_PARSED` stdout echo
that `265fe2a1` lacks.  Per the instruction, "FCT strings identical" is NOT
sufficient to prove event-level trajectory identity.

Therefore **every actuation -> performance statement in this round is labelled
`CROSS_RUN_DIAGNOSTIC` and is not a causal result.**

The clean fix (not performed this round, as instructed): add only
`CBAP_ACTUATION_FILE` to the ckpt4 CBAP config, re-run S3 once under binary
`290cb41f`, and verify every core output byte-identical except the new log.
Estimated cost: ~18 min, ~120 MB.

## Inputs actually used

| purpose | file | sha256 |
|---|---|---|
| stage timestamps | rec2_s3_on_out/actuation.csv | %s |
| queue / zone / boost | ckpt4_cbap_s3_out/qc_trace.csv | %s |
| served rate | ckpt4_cbap_s3_out/selected_link_timeseries.csv | %s |

Window: W2 = [2.000000000, 2.058372997] s.  Sample interval 10 us (verified
uniform, n=5838, min=max=1.0e-5 s).
"""

RECON = """# ACTUATION COUNT RECONCILIATION

## The two "superseded" numbers have different definitions -- both now closed

### My ledger: SUPERSEDED_BEFORE_EFFECT = 394
Primary key `(run_id, link_id, flow_id, generation_id)`.
Definition: a generation that has a `rate_command` row but **no**
`sender_rate_effect` row anywhere in the file.
Scope: all 609 generations, all 64 incast flows + background, whole run.

### Writer counter: superseded = 340
Source: `scratch/third.cc:893`
```cpp
if (cbap_actuation_pending.count(k))
        cbap_act_superseded++;
```
Key `k` is `CbapActuationKey{sip,dip,sport,dport,pg}` -- a **per-QP 5-tuple**,
not a generation id.  It increments only when a NEW command arrives while the
PREVIOUS command for that same QP is **still in the pending map** (i.e. not yet
seen at the sender).  A generation that never reaches the sender but whose
successor arrives *after* the map entry was already cleared is NOT counted.

### Reconciliation (independent recount)
Emulating the writer's rule on the canonical ledger -- count a command whose
immediately-preceding command for the same flow had not yet been seen at the
sender -- yields **340**, exactly matching the writer.

```
394  generations with no sender_rate_effect          (my definition)
340  displacement events of a still-pending entry    (writer definition)
 54  difference
```

And **54 == the writer's `pending` counter**: 54 generations were still pending
in the map when the run ended, so they never had a successor to displace them.

```
394 = 340 (displaced) + 54 (still pending at end of run)
```

### Identity check
```
total     = 609
APPLIED   = 215
SUPERSEDED_BEFORE_EFFECT = 394
SUPERSEDED_AFTER_EFFECT  = 0
UNMATCHED_NO_COMMAND     = 0
sum       = 609  == total   PASS

writer:  unmatched=0  superseded=340  negative=0  pending=54  inflight=0
         340 + 54 = 394                            PASS
```

**A. The 394 and 340 figures are fully reconciled.**  A single canonical ledger
is retained: `ACTUATION_LEDGER_CANONICAL.csv.gz`, 609 rows, keyed by
`(run_id, link_id, flow_id, generation_id)`.
"""

BYTE = """# BYTE DOMAIN AUDIT

## Chain of custody for served rate

| quantity | source | domain | verified how |
|---|---|---|---|
| `m_txBytes[if]` | `switch-node.cc:450`: `m_txBytes[ifIndex] += p->GetSize()` | **WIRE bytes** | source read |
| `GetTxBytes(if)` | `switch-node.cc:261` returns `m_txBytes[if]` | WIRE | source read |
| `tx_bytes_delta` | `LinkTraceTick`: `dt = tx - trace_last_tx[l]` | WIRE bytes per sample | source read |
| `utilization` (writer col) | `dt*8.0/(crfm_trace_sample_us*1e-6)/GetDataRate()` | ratio of WIRE bps to link bps | source read |
| `served_wire_rate` (my DERIVED) | `8*tx_bytes_delta/DT`, DT = 10 us | WIRE bps | recomputed |
| capacity C | `d->GetDataRate().GetBitRate()` = 10e9 | WIRE bps | config + source |

## The payload/wire confusion hypothesis is REJECTED

```
10 / 1.048        = 9.541985 Gbps
measured served   = 9.576401 Gbps      <- ABOVE 10/1.048
9.576401 * 1.048  = 10.036068 Gbps     <- would EXCEED C, impossible
```
If the figure were payload bytes mislabelled as wire, it would have to be at or
below 9.541985.  It is not.  Both directions of the conversion are inconsistent
with a domain error.

## Independent cross-check against the writer's own column

My DERIVED utilisation, computed from `tx_bytes_delta` with DT = 10 us, versus
the `utilization` column the simulator wrote itself:

```
derived mean = 0.957640        writer mean = 0.957640
derived max  = 1.006080        writer max  = 1.006080
```
Agreement to 6 decimal places over n = 5838 samples.  Sample interval verified
uniform: `CRFM_TRACE_SAMPLE_US 10`, measured dt min = max = 1.0e-5 s.

Note `max utilisation = 1.006080 > 1`: that is the whole-packet quantisation
already characterised (a 10 us window holds 11.92 packets of 1048 B, so a window
completing 12 whole packets measures 1.00608 C).  Not a domain error.

**C. The served-rate byte domain is CLOSED.**  `B_deficit` = 3,420,068 B (CBAP)
and 1,301,512 B (DCQCN), excess 2,118,556 B, are hereby re-labelled from
`UNVERIFIED_ACCOUNTING` to **DERIVED (wire domain, verified)**.
"""

CAUSAL = """# CAUSAL DECISION

## What the evidence supports

Permitted statement only:
> command cadence and end-to-end effect latency are scale-mismatched, and a
> large number of generations are replaced before taking effect.

## Item 4: D2 split -- the delay is physical, not controller loss

| sub-stage | n | mean | p95 | max | nature |
|---|---|---|---|---|---|
| D2a sender -> bottleneck arrival | 215 | **64,833 ns** | 78,393 | 84,998 | propagation + upstream queueing |
| D2b bottleneck queue -> egress | 215 | **19,689 ns** | 37,341 | 43,150 | egress queueing + serialization |
| D2 total | 215 | **84,522 ns** | 115,130 | 117,779 | |

D2a + D2b are both physical transport terms.  Neither is an
"optimisable control delay": D2a is flight time of data already in the network,
D2b is the bottleneck's own service time.  **76.7 % of D2 is D2a.**

For reference D1 (command -> sender) = 20,223 ns mean, the only stage that is
plausibly software-side.

## Item 5: supersession semantics -- 394 classified

| class | count | fraction of superseded |
|---|---|---|
| `redundant_same_direction` | **339** | 86.04 % |
| `indeterminate` (still pending at run end) | 54 | 13.71 % |
| `harmful_lost_decrease` | **1** | 0.25 % |
| **`harmful_lost_increase`** | **0** | **0.00 %** |
| `safety_correction` | 0 | 0 |

`harmful_lost_increase` -- a rate *increase* overwritten by a *lower* target
while the queue was in the safe zone -- occurs **zero times**.  Attributable
lost bytes from that class: **0 B**.

The 339 `redundant_same_direction` cases are commands superseded by a target in
the same or higher direction: the replacement did not withdraw the increase, so
no increase was lost.

## Item 6: effect-aligned tracking

Over all 11,675 W2 epochs, **every** epoch is `safe_green` (zone GREEN and
q0 < Q_low = 524,288 B).  Of those, **3,021 epochs (25.87 %)** have measured
served rate below 0.99 C.  Integrated shortfall in those epochs:
**6,839,164 B**.

That 6.84 MB exceeds the total measured `B_deficit` of 3.42 MB, because the
per-epoch threshold (0.99 C) is stricter than the deficit integral's (1.00 C
with only positive parts). Both point the same way: the link is persistently a
few percent under line rate while the queue is deep in the safe zone.

## Item 7: is a controller change justified?

The gate was: proceed only if `harmful_lost_increase` explains an observable
excess service deficit **and** aligns in direction and time with the 1.033590 ms
tail gap.

- `harmful_lost_increase` count = **0**
- attributable bytes = **0 B**
- therefore it explains **0 %** of the 2,118,556 B excess deficit

**Conclusion (required wording):**
> Supersession is frequent, but there is no evidence that it is harmful.

`actuator coalescing` is **NOT authorised** by this evidence.  Implementing it
would target a mechanism whose measured harm is zero.

## Where the deficit is NOT explained

Established negatives, so the next investigation does not repeat them:
- not idleness: idle fraction = 0.000000
- not queue starvation: queue mean 23,957 B, 100 % of epochs in GREEN
- not a byte-domain error: verified against the writer's own column
- not lost boost commands: harmful_lost_increase = 0
- not GREEN under-boosting per se: boost non-zero in 99.65 % of epochs

Remaining candidates, in the order the data favours:
1. **work conservation / burstiness at 10 us granularity** -- served rate max is
   1.00608 C and mean 0.9576 C with zero idle, which is the signature of
   packet-level gaps rather than a rate-setting error.
2. **per-QP pacing / packetization floor** -- 64 flows each paced at ~136 Mbps
   over 1048 B packets gives an inter-packet gap of ~61 us; sub-packet rate
   resolution cannot be realised inside a 10 us sample.
3. **arrival-side accounting** -- `applied_rate_audit.csv` has
   `actual_arrival_excess_bps` and `rate_clamp_delta_sum_bps` that were not
   examined this round.

None of these is claimed as the cause.

## E. Authorisation

**Not authorised** to implement actuator coalescing.  The evidence closes items
1, 3, 4, 5, 6 but returns a null result on harm, and item 2 leaves all
actuation -> performance links as CROSS_RUN_DIAGNOSTIC.
"""


def main():
    third = '/work/simulation/scratch/third.cc'
    open(os.path.join(D, 'ACTUATION_PROVENANCE.md'), 'w').write(
        PROV % (sha(third), sha(os.path.join(B, 'rec2_s3_on.txt')),
                sha(os.path.join(B, 'ckpt4_cbap_s3.txt')),
                sha(os.path.join(B, 'rec2_s3_on_out/actuation.csv')),
                sha(os.path.join(B, 'ckpt4_cbap_s3_out/qc_trace.csv')),
                sha(os.path.join(B, 'ckpt4_cbap_s3_out/selected_link_timeseries.csv'))))
    open(os.path.join(D, 'ACTUATION_COUNT_RECONCILIATION.md'), 'w').write(RECON)
    open(os.path.join(D, 'BYTE_DOMAIN_AUDIT.md'), 'w').write(BYTE)
    open(os.path.join(D, 'CAUSAL_DECISION.md'), 'w').write(CAUSAL)
    names = sorted(f for f in os.listdir(D) if os.path.isfile(os.path.join(D, f)))
    with open(os.path.join(D, 'SHA256SUMS.txt'), 'w') as fh:
        for f in names:
            if f == 'SHA256SUMS.txt':
                continue
            fh.write('%s  %s\n' % (sha(os.path.join(D, f)), f))
    print('written')
    for f in names:
        if f != 'SHA256SUMS.txt':
            print('%s  %s' % (sha(os.path.join(D, f))[:16], f))


main()
