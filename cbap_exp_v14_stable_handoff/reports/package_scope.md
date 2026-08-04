# CBAP-v1.4 validation package scope

This package contains the complete analysis reports, processed audit tables,
manifests, case inputs, scripts, static tests, and compact per-run metadata and
summary outputs for all semantic and deterministic-validation runs.

The following high-volume raw diagnostics are intentionally excluded from the
portable result package: `sender_tx_trace.csv`, `cbap_rate_transitions.csv`,
`cbap_port_summary.csv`, packet traces, and sampled flow/link time series. They
remain in the repository run directories. Their exclusion does not remove any
run, scenario, aggregate result, handoff decision, completion record, input
hash, validity decision, or reported comparison.

`package_manifest.csv` records the size and SHA256 digest of included files.
The package is an ns-3 deterministic single-seed result archive; it is not a
multi-seed statistical or deployment artifact.
