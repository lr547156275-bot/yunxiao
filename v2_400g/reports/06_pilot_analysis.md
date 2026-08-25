# v2_400g — Pilot analysis (67/67 cells, data: reports/03_pilot_results.csv)

Arms: cbap (D_target=8µs, BMAX=0.02, H_GUARD measured 118/15/12µs),
cbap0 (boost-off ablation), hpcc (stock), dcqs (DCQCN stock),
dcqn (speed-normalized: AI=0.005C, HAI=0.01C), dcql (dcqn + delay-defined
low ECN: KMIN=2µs, KMAX=8µs of line rate — the user-requested
"trade FCT/goodput for queue" arm).

## Findings

1. **Queue separation grows with rate.** CBAP bottleneck queue delay:
   7–43µs at 400G, 15–23µs at 200G, vs baselines 255–450µs (400G) and
   498–814µs (200G). At 10G large messages CBAP degrades to the backend
   ECN equilibrium (~1000µs) — see finding 6.
2. **Buffer-filling vs buffer-invariant.** 400G×4MiB buffer sweep: baseline
   queue scales with the buffer (2.7 → 10.7 → 21.4MB over 8/32/64MB;
   PFC 2442 → 792 → 322–812), CBAP constant 0.49MB, PFC 0 at every size.
3. **Batch completion (p99 CCT, the collective metric): CBAP wins wherever
   the message ≥ BDP, and the margin widens with rate.** p99/ideal-drain at
   16MiB: 10G tie (1.013 vs 1.014) → 200G 1.015 vs 1.082 → 400G 1.026 vs
   1.110. Baselines' better *mean* CCT at small sizes reflects unfair
   staggered completion, not faster collectives.
4. **Honest boundary: msg < BDP (256KiB at 200/400G) CBAP p99 is 1–3%
   behind the best baseline arm** — admission overhead outweighs congestion
   control when the burst is self-draining. Queue is still 30–60× lower.
5. **Background retention.** CBAP holds the exact 0.8C payload cap at every
   rate/size. dcqs (stock AI=50M) collapses at high rate (12G of 304G at
   400G×16MiB) — the speed-normalization argument made concrete; dcqn
   recovers to ~186G; still below CBAP.
6. **v2 uniform D_abs=80µs is infeasible at 10G.** Q_abs=100KB there, but
   the MIN_RATE floors (64×0.01C + bg floor ≈ 0.65C) make the admission
   transient overshoot unavoidable; measured peak ~1.1MB (settles at the
   backend ECN equilibrium). The blind-window bound explains the rate
   asymmetry: C×H_eff/8 = 147KB (10G) > Q_abs, vs 375KB ≪ 2MB (200G) and
   600KB ≪ 4MB (400G). Fix in section 07 (feasibility rule, not tuning).
7. **Ablation (400G×4MiB): boost improves mean CCT +4.8% but worsens p99
   −2.2%** and adds ~0.1MB queue. The predictive-boost benefit measured at
   10G (−2.6% CCT in v1) degrades to a mean/tail tradeoff at 400G —
   the mechanism-vs-rate story, quantified.
8. Five incomplete cells, all 10G large-message baselines (hpcc 4m n=9,
   16m n=0; dcq* 16m n=27..57): pilot stop gave only ideal×1.037; unfair
   completion needs more. CBAP finished 64/64 everywhere. Formal matrix
   rule: stop = release + ideal×1.3 + tail; any incomplete cell ⇒ extend
   the whole scenario and rerun it (never one arm silently).
9. Harness consistency: dcqs ≡ dcqn at 10G byte-identically (0.005C = 50M
   = stock there), as expected.

## Consequences adopted into the formal design

- Q_abs feasibility rule (07 §A), stop rule (07 §B), 256KiB kept as an
  honest-boundary scenario, dcqs demoted to annex (its collapse is a
  finding, not a competitive baseline), buffer sweep and ablation kept.
