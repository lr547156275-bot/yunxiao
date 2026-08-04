# PFC semantic audit report

## Verdict

`PFC_SEMANTICS_EXPLICIT_NO_TRIGGER`

All nine seed-1 semantic-audit runs passed the output, input-hash, completion,
event-schema, port/PG, and sender dequeue-gate checks.

- All six runtime-PFC-enabled cases completed with the explicit classification
  `PFC_NOT_TRIGGERED`: the audited PFC thresholds were never crossed, so an
  end-to-end pause event chain was not exercised.
- All three runtime-disabled controls completed with
  `PFC_DISABLED_CONFIRMED` and observed zero events.
- No absent file or missing event was replaced with zero.
- The queue trace object (`BEgressQueue`) and PFC decision object
  (`SwitchMmu`) are explicitly distinguished.

Consequently, PFC event counts in the planned Clos experiment must be reported
as `NA` unless a future run produces and validates a complete six-event chain.
This is a clear simulator-semantic conclusion, not evidence that PFC pause
delivery was dynamically exercised.

The machine-readable evidence is
`bop_exp/main_v2/analysis/pfc_semantic_audit.csv`; the validation contract is
`bop_exp/final_preflight/pfc_audit_contract.md`.
