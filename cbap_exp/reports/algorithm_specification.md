# CBAP-v0 algorithm specification

CBAP-v0 uses modes 20--23 because mode 16 was already occupied. Mode 20 is
the independent-min-grant diagnostic, 21 is batch admission followed by
DCQCN, 22 is closed-loop rate-only CBAP, and 23 is full rate-plus-credit
CBAP. The frozen BOP-QB remains mode 15.

At application readiness, every member of one round group is planned as one
batch. DATA becomes eligible only after the configured 5-us planning delay.
Each controlled link contributes its most recently delivered, completed
5-us port epoch. A summary itself arrives after a 5-us scheduled control
delay and is counted as a 64-byte logical message.

The port state is one of CLEAR, STABLE, ROOT_CONGESTED, PROPAGATED, or
MIXED_OR_UNCERTAIN. Queue thresholds are 0.25, 0.50, and 0.80 of the actual
configured ECN threshold. Arrival, service, and queue gradient are computed
from cumulative switch counters over the completed epoch. PROPAGATED does
not create a second root.

Admission protects an incumbent at 90% of its two most recent epoch sending
rates, scaling floors when infeasible. Pending flows are allocated together
by equal-weight progressive filling. Queue room below 0.5 ECN provides a
temporary rate allowance over the estimated feedback horizon and a separate
one-shot byte credit. An end-to-end flow always takes its minimum path grant;
no per-link multiplicative rate penalties are applied.

After fresh summaries cover the whole path, rate-only and full variants enter
TRACKING. Increases require two CLEAR/STABLE epochs and are bounded by the
path target, 10%, 2 Gbit/s, and NIC maximum. Normal decreases move once to
the path minimum grant. Severe queue/PFC evidence enters RECOVERY, clears
credit, freezes increase for two epochs, and uses the registered emergency
bound. Stale or uncertain feedback cannot increase a rate.

Full CBAP additionally meters every real wire DATA packet. Base service
accumulates at `base_rate`; bytes above it consume the batch's nonrefillable
credit. Packet pacing is still performed by the existing QP/NIC scheduler.
No CBAP DATA header is added.
