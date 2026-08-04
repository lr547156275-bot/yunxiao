# Suspicious findings

- BOP-QB records estimated_q0=0 in every residual run despite actual q0 of 71,940 B or 179,850 B.
- residual_160k BOP-QB produces 85 ECN marks across three seeds; Oracle-q0 produces 4.
- The logged estimate-based safety flag passes for BOP-QB, but the actual-q0 replay fails in both residual scenarios.
- Oracle-q0 changes queue and ECN but not group RCT in either residual scenario; this is evidence for safety/queue value, not an RCT improvement claim.
