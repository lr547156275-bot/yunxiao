# Control overhead report

- Scoped run control messages: min 20030, max 306188.
- Scoped control bytes: min 1281408, max 15016992.
- Maximum control/DATA-wire ratio: 8.443%.
- Maximum grants per pending flow: 1.000.

`processed/control_overhead.csv` exposes decision, port-summary, grant, bandwidth, frequency, and wire-byte-normalized fields by fan-in, message size, and incumbent load. Per-flow grant processing remains a potential deployment bottleneck at high fan-in; the simulator measures messages and bytes, not CPU cost.
