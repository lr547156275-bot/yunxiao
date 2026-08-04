# Controller ownership contract

During phase 8, `DCQCN_DESIRED` may update only desired state. `ENVELOPE_PROJECTOR` may update only `m_rate`, `m_nextAvail`, and pause/resume pacing state. Full CBAP tracking excludes delegated flows. Every projected flow row records the two fixed writer names, and the semantic analyzer rejects any phase-8 `CBAP` applied-rate write.
