# Suspicious findings and audit notes

- No run was selectively removed; invalid run count: 0.
- Seed-level variation is often small because topology and workload are deterministic except for bounded release jitter; three seeds must not be presented as broad statistical stability.
- Queue p95 is zero in multiple short-message runs while queue max is nonzero. This is consistent with sparse burst occupancy under the recorded sampling distribution; queue-max conclusions should not be substituted with p95 conclusions.
- Some short-message baselines tie because feedback arrives too late to materially change the short round. Ties are retained.
- BOP-QB does not have the lowest RCT in every scenario. All adverse RCT changes are retained in best_baseline_comparison.csv.
- `NA` dropped/retransmitted/control-byte fields remain unavailable and are not converted to zero.
- Wire-Equalized DCQCN is diagnostic-only and is excluded from the main external-baseline selection.
