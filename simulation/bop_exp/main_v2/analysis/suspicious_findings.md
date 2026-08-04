# Suspicious findings

1. `main_v2/audit_runs` is empty: the required nine event-level PFC audits were not run. Missing counters remain NA.
2. Historical queue statistics and PFC decisions use different accounting objects, so old zero PFC counts do not verify semantics.
3. n32 DCQCN differs by 48.840 us (+22.91%) from the archived report; the archive lacks the raw legacy inputs.
4. All 273 current formal entries pass reuse validation. Their rerun is forbidden by the task and would not recover legacy evidence.
