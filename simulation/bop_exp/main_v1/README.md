# BOP-QB Main Experiments v1

This directory freezes the formal BOP-QB implementation at `CC_MODE=15` and
`BOP_QB_QUEUE_FRACTION=0.50`. It prepares the 318-run, three-seed paper matrix
without changing the congestion-control algorithms.

The generated manifest has 270 main runs, 30 mechanism-ablation runs, and 18
wire-fairness runs. `completed.flag` is created only after the simulator exits
successfully and all output checks pass. Failed runs retain their raw outputs.

No experiment result is included in this framework.

Audit and validity documentation is under `docs/`. The paper chapter skeleton
is under `paper/experiments/`. Run scripts default to `JOBS=1`, keep failed raw
outputs, refuse low-disk launches, validate frozen/input hashes before reuse,
and never convert invalid runs to zero-valued records.
