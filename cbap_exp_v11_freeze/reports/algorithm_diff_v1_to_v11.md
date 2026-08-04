# CBAP-v1 to CBAP-v1.1 algorithm difference

Both versions use the same CC_MODE 22 (Rate-Only) or 23 (Full), admission
planner, feedback state machine, rate-decrease rules, queue credit and packet
pacer.

- v1 / `legacy_min`: `delta = min(0.10 * current, 2 Gbit/s)`.
- v1.1 / `adaptive_max`: `delta = max(0.10 * current, 2 Gbit/s)`.
- Both: `new = min(target, current + delta, max_rate)`.

The existing increase preconditions remain in their original order: TRACKING,
no freeze, complete fresh feedback, no root/propagated/mixed ambiguity, two
CLEAR/STABLE epochs, and target more than 5% above current. Stale or incomplete
feedback cannot reach the increase branch.

`CBAP_INCREASE_POLICY=0` is the backward-compatible default. The fraction and
absolute increment are parsed but frozen by validation to 0.10 and
2,000,000,000 bit/s; this is not a tuning interface.
