# D-round conclusions — FROZEN (S3, single seed, 2026-08)

Source data: `d1_dcqcn_out/ d2_caponly_out/ d3_capmig_out/ d4_capmigband_out/`,
metrics `d1234_metrics_v2.csv`, ownership `per_flow_control_ownership.csv`.
None of these directories may be modified or deleted; the D4v2 screening round
uses fresh `scr7_*` directories.

## Frozen verdicts

| arm | verdict |
|---|---|
| D1 | DCQCN-only baseline |
| D2 | static cap, NO migration — severe loss: CCT +43.5%, goodput −30.3% vs D1. Migration is necessary, not optional. |
| D3 | static cap + active migration — current reliable operating point |
| D4v1 | old queue-band (+0.30C on top of 1.0C cap) — **INVALID_OVERBOOST_POLICY**. Evidence retained in `d4_capmigband_out/`, not overwritten. |

## D3 vs D1 (unified metrics, both measured from t=2.000000000 s)

| metric | D3 | D1 | delta |
|---|---|---|---|
| CCT (ms) | 58.4911 | 58.3730 | +0.20% (slower) |
| batch goodput (Gbps) | 9.1787 | 9.1972 | −0.20% |
| queue max (B) | 9,432 | 1,279,608 | 135.7× lower |
| q-delay max (µs) | 7.55 | 1,023.69 | 135.6× lower |
| samples over Q_abs | 0 | 1,833 | — |
| PFC / drops / retx | 0/0/0 | 0/0/0 | — |

D3's steady-cap, migration, rho and all other behaviour are frozen; D4v2 is an
independent, default-off mode whose baseline plan equals D3 exactly.

## D4v1 failure mechanism (why the policy, not the machinery, was wrong)

The band term was real (queue 9,432 → 1,196,816 B; in-window migration
dispatches 13,641 vs 11,777), but it stacked up to +0.30C on top of a static
cap already at 1.000C — a sustained target of ~1.3C that can only fill the
buffer: CCT +22.1%, goodput −18.1% vs D3, 3,380 samples over Q_abs.
D4v2 therefore uses a small leased top-up (BMAX ≤ 0.08C screened, hard-capped
at 0.10C in config parsing) driven by predicted queue headroom, not a
permanent additive boost.

## Background-flow evaluation — corrected口径

The old hard gate "retention ≥ 99% inside the incast window" is REMOVED: D1
itself fails it (in-window bg rate ≈ 3% of pre-window), so it measured the
scenario, not the algorithm. Replaced by four explicit figures, each also as a
ratio vs same-seed D1: full-run goodput, in-window goodput, outside-window
goodput, and recovery time to 95% of the pre-handoff rate after the batch.
Hard gates keep only: bg_full/D1 ≥ 99%, bg_outside/D1 ≥ 99%, PFC=0, drop=0,
retx=0, 64/64 incast completed, qmax ≤ Q_abs. The in-window dip is reported as
an explicit trade-off.

## Single-seed discipline

Any |difference| < 0.3% vs D1 on one seed is a TIE_CANDIDATE — no win/loss
claim until confirmed by multi-seed paired runs.
