# Suspicious and adverse findings

- No run-level invalidity, input-hash mismatch, fixed-path mismatch, collective-byte mismatch, barrier overlap, NaN/Inf, log truncation, formula error, capacity violation, or per-link credit violation was found.
- Clos PFC counts remain `NA`: the nine-run event-level PFC audit validates the measurement semantics but does not justify replacing unavailable Clos PFC observations with zero.
- The current source hash differs from the older single-bottleneck and n32 replay runs because the default-off Clos extension was added later. The 273 stored historical hashes remain internally consistent, the single-bottleneck regression flag passes, and all three stored n32 replays match their source runs exactly.
- DCTCP has the lowest mean CCT among the four formal CC baselines in all 16 Clos scenarios. BOP-QB is 5.31%–29.13% slower than that best baseline in every Clos scenario.
- BOP-QB does not preserve a universal low-queue advantage in Clos: its mean queue maximum is lower than the best formal baseline in 7/16 scenarios and higher in 9/16.
- The largest adverse CCT results are the 64-rank 1 MiB ring (+29.13%) and hierarchical (+26.87%) cases. These results are retained.
- The largest adverse queue results are 32-rank 1 MiB hierarchical (+264.32%), 2:1 64-rank ring (+155.29%), and 1:1 64-rank ring (+153.50%). These results are retained.
- In the DLRM-like sequence, BOP-QB is 8.04% slower than DCTCP, while reducing queue maximum by 56.91% and ECN marks by 95.00%; this is a tradeoff, not an unqualified win.
- Three seeds only measure repeatability over the configured jitter. The paired 95% t intervals use three scenario-level seed pairs (df=2); steps and rounds are never treated as independent samples.
