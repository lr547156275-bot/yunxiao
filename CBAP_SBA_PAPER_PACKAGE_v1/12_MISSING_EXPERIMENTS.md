# Missing / not-run experiments (do NOT cite as evidence)

1. Multi-seed & perturbation study: the simulator is deterministic (proven
   bit-identical across seeds), so seed replication is uninformative; a
   perturbation study (arrival jitter, source permutation) was designed but
   NOT run. Cross-random-environment generalization must not be claimed.
2. Baseline parameter sweep exists on S3 only (21 points); other scenarios
   use standard defaults. Frontier dominance is an S3 statement.
3. TIMELY T_LOW/T_HIGH/alpha/beta not exposed by the harness config parser;
   its sweep covers RATE_AI only.
4. CBAP Q_target and rho were not re-swept after the ledger fix (rho was
   swept only in superseded pre-D4v2 rounds); Q_target=0.025*Q_abs is a
   design choice with untested sensitivity.
5. Multi-round iterative batches (S7) and victim short-flow latency (S8)
   were designed, predicted to enlarge the gap, and NOT run.
6. Multi-hop topologies / PFC head-of-line effects: not measured (single-
   hop bottlenecks only; S6 is dual-bottleneck, still single-hop).
7. Admission does not bound the infeasible-floor overlap duration
   (envelope T~2.2ms quantified); a duration-budget admission check is
   future work.
8. Concurrent controlled-flow count > ~94 is refused by MIN_RATE floor
   feasibility (design envelope), so larger fan-in was not evaluated.
9. RTT/topology variation beyond the fixed testbed: not run.
Packaging incident log: the initial cross-check flagged 10 S4/S5 rows;
root cause was the packaging script aggregating the background round's
injection_end (correction 10 in 11_CORRECTIONS). After restricting to
incast rounds, no contradictions between data, configs, logs and metric
definitions remain (timestamp ordering cross-check: 30/30 OK).
