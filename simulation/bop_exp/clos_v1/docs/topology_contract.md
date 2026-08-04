# Frozen topology and protocol contract

The Clos configurations inherit the frozen main-v2 link and protocol values:

| Item | Value |
|---|---:|
| Host–leaf and leaf–spine rate | 100 Gbit/s |
| One-way link propagation delay | 0.001 ms |
| Packet payload | 1000 B |
| BOP packet accounting unit | 1024 B |
| Switch buffer | 32 MiB |
| ECN Kmin | 400 KB |
| ECN Kmax | 1600 KB |
| ECN Pmax | 0.2 |
| PFC pause time | 5 us |
| BOP rho | 1.0 |
| Formal Clos background load | 0 bit/s |
| BOP-QB target | 0.5 × ECN Kmin |

`clos_1to1_64h` has 64 hosts, eight leaves with eight hosts each, and eight
spines. `clos_2to1_64h` has the same host/leaf layout and four spines.
All switch DATA egresses are explicitly identified in
`multilink_links.txt`. This includes each host NIC output because multiple
destination QPs share that sender link. Host outputs do not fabricate an INT
hop: after the preceding global barrier their legal release-time queue prior
is zero. Interface IDs are derived from topology-file link order, not guessed.

The first 32 hosts (the first four leaves) form 32-participant cases. All 64
hosts form 64-participant cases. Each inter-leaf flow has one seed-determined,
fixed spine for its entire QP lifetime. Intra-leaf flows have no spine hop.

PFC event instrumentation exists, but the preflight event chain did not
validate a triggered PFC episode. Consequently the formal Clos parser records
PFC as `NA`. It never converts “not observed” into zero.
