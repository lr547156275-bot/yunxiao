# TriSTATE cleanup report

The complete previous experiment directory was moved, without deleting its
results, to:

`research_archive/tristate_stop_20260727_190225`

The live `tristate_exp` directory no longer exists. Using the archived patch and
the current diff as guides, cleanup removed the TriSTATE-only CC modes,
configuration fields, QP state, RTT state machine, initialization, control
handler, and experiment-only sampling hooks. HPCC, DCQCN, TIMELY, fixed-path
support, switch counters, PFC state access, and bounded generic tracing were
retained.

The required broad source grep has no TriSTATE experiment runtime match. It
does find one pre-existing sentence in
`src/internet/model/global-router-interface.h` describing a generic SPF
“tristate flag.” That comment is unrelated to congestion control and was not
changed merely to make a text search empty.

No simulation was executed during cleanup or implementation.
