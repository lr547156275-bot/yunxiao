# ACTUATION COUNT RECONCILIATION

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
