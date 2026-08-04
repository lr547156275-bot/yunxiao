# Suspicious findings

- No run-level capacity, credit, completion, NaN or truncation failure was detected.
- E3 is `SCENARIO_NOT_STRESSFUL`: DCQCN PFC-on and PFC-off are identical, no PFC event occurs, and the victim-throughput ratio is 0.999993.
- Sampled mean utilization can slightly exceed 1.0 because retained 10-us counter windows include boundary serialization; this is not a physical >100% capacity claim.
- Full root-link audit has 6 detected true-link rows, 0 false-link rows and 0 propagated-as-root rows. Exact onset-based latency and epoch recall are not measurable from the retained ground truth.
- Init-Only has nine propagated-as-root/false-root link rows; Full has none. This handoff issue does not rescue Full's FCT failures.
- Exact host-side packet pacing cannot be audited from switch dequeue timestamps and is not claimed.
- Independent admission oversubscribes the reconstructed E2 budget by up to 619.317 Gbit/s; batch admission removes this violation.
- Repository-wide `git diff --check` reports CRLF/trailing-space hunks in the already-dirty `third.cc`; the same hunks are present in `preflight/preexisting_changes.patch`. The CBAP model-header/source subset passes `git diff --check`, so the shared file was not mass-reformatted.
