# BYTE DOMAIN AUDIT

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
