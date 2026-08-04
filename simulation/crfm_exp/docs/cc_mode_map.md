# CC mode map

Modes found in the actual `RdmaHw` dispatch:

| Mode | Controller |
|---:|---|
| 0 | no congestion controller |
| 1 | DCQCN |
| 3 | HPCC |
| 7 | TIMELY |
| 8 | DCTCP |
| 10 | HPCC-PINT |
| 11 | HPCC round reset (diagnostic oracle) |
| 12 | CRFM gate |
| 13 | RS-HPCC |

Modes 11, 12, and 13 were a continuous unused range. Mode 13 now contains
Round-Safe HPCC; the former empirical carry/recovery implementation is
disabled. Mode 3 and mode 1 were not renumbered or repurposed. `ROUND_MODE=0`
rejects modes 11--13 and retains the normal flow byte limit and dispatch.
