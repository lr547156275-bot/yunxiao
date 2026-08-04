# BOP-QB multi-link Clos framework

This directory contains inputs and manual runners for the frozen BOP-QB
multi-link validation. It does not contain simulation results.

The prerequisite audits concluded:

- `N32_CURRENT_CONFIG_DETERMINISTIC`;
- `PFC_SEMANTICS_EXPLICIT_NO_TRIGGER` (therefore formal Clos PFC metrics are
  reported as `NA`, not zero);
- `SINGLE_BOTTLENECK_HARDCODED`, with a valid path to implement only the
  already-defined multi-link `T_star` and QB-credit equations.

Before any Clos run, execute the three-case single-bottleneck regression.
Clos runners refuse to start unless it creates
`single_bottleneck_regression/PASS.flag`.

The `dlrm_like_64h` case is a size-driven synthetic communication sequence,
not a real GPU training trace.

No simulator was run while this framework was implemented.

