# Semantic verification

- Positive target/applied mismatched epoch rows: 0.
- Applied capacity violations: 0.
- Floor clamp count: 0.
- Sender pacing violations: 0.
- Fan64 v1.3 rows fixed at 108.9536 Gb/s: 0.
- Zero-grant DATA transmissions during pause: 0.
- Zero-grant pause duration: 15000 ns.

Low-rate packet timing is checked against `ceil(8*actual_wire_bytes*1e9/rate)`; smaller tail packets are not incorrectly required to use the maximum-packet interval.
