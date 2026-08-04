# Ablation report

The deterministic small (fan4/64 KiB), middle (fan16/1 MiB), and large (fan64/4 MiB), all load-80%, rows compare Independent-Min-Grant, Init-Only, RateOnly-v1.1, Unscoped Full-v1.1, and Scoped Full-v1.1. Exact CCT, queue, AUC, utilization, and control metrics are in `processed/ablation_summary.csv`.

The table separates batch-joint admission (versus independent), continuing rate tracking (versus Init-Only), credit/rate behavior (RateOnly versus Full), and structural scope (Unscoped versus Scoped). These three deterministic points do not establish broad statistical generality.
