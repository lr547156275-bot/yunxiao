# Corrections and provenance (old conclusion -> final conclusion)

1. **pg=0 background runs invalidated.** Early rounds ran the background
   flow on priority group 0; all final inputs use pg=3 (verified in every
   committed flow file, column 3). Impact: any pre-pg3 numbers are
   unusable; none appear in this package.
2. **Migration actuation was invisible.** EvaluateCbapSbaMigration() calls
   ChangeRate() directly and never wrote rate_transition.csv; ~48% of all
   rate commands (11,777/24,449 in-window on S3) were unrecorded. Fixed by
   actuation_kind tagging (fixAD/AE); byte-identity of 9 result files
   proved instrumentation-neutrality. Final evidence: 05_CONTROL_TIMELINE.
3. **"The background flow is not controlled by CBAP" -- RETRACTED.** The
   old per-flow census read only the SetCbapRate path, which issues 0
   in-window commands to the background flow; the migration path drives it
   8G->0.1G->8G with 55 in-window dispatches. Final: 05_CONTROL_TIMELINE.
4. **Wire/payload accounting.** (a) pacing used 1048/1000 wire bytes vs
   payload budgets (4.8% underfeed) -- fixed in the steady-state fill;
   (b) the SBA initial-release check compared wire-domain old rates against
   payload-domain capacity (available == C*1000/1048 exactly), making any
   admission on a saturated link impossible -- replaced by the occupancy
   bound (fixAK), byte-identical on all frozen runs; (c) grant budgets
   retain a ~4.6% mixed-domain startup transient (documented debt, not
   fixed by decision).
5. **LEDGER_GHOST_ARRIVAL.** A down-to-zero boost command computed per-QP
   share = 0 and never cleared commandedWireBps, so a stale arrival ghost
   (constant 26,528 B envelope) suppressed the boost law indefinitely.
   Fixed (fixAH) with a python mirror unit test (7/7); all pre-fix v2
   screening numbers (scr7 ladder) are marked INVALID_LEDGER_GHOST_BIAS.
6. **Recorder/clipping corrections (earlier campaign).** Single-link TX
   recorder expectations and QLEN_MON_END < stop-time clipping were fixed
   before this campaign's rounds; matrix cells route qlen to /dev/null
   after an unguarded fopen (third.cc:5024) segfaulted a slimmed run
   (2026-08-20, all 30 cells rc=139) -- twin byte-regression then proved
   the /dev/null variant behaviour-neutral.
7. **Floor/control-generation sets.** The controller floor covers the
   FLOOR set (background included exactly once), not the steered set;
   earlier double-count produced a 6.600G floor artifact (fixed pre-matrix,
   "DEFECT C" comments in rdma-hw.cc).
8. **CCT/BCT/FCT naming.** flow_summary.fct mixes definitions across
   algorithms (CCT for CBAP, FCT for baselines) and an early report used a
   batch window as both CCT and BCT; final definitions are frozen in
   01_METRIC_DEFINITIONS.md and all package numbers use flow_timing.csv.
9. **Superseded artifacts.** scr7 v2 ladder (ledger bias); D4v1
   (+0.30C band) = INVALID_OVERBOOST_POLICY, evidence retained; the old
   "ADMISSION_FAILFAST_ON_INFEASIBLE_FLOORS" label was RELABELLED to the
   domain artifact of correction 4b (census-proven, margin independent of
   batch size); pa/mb/telemetry rounds superseded with summaries retained.
   Full run status: 00_RUN_INVENTORY.csv.
10. **injection_end aggregation artifact (packaging).** The first package
   build and matrix_report.md's S4/S5 injection_end row took max() over ALL
   rounds, so the BACKGROUND round's injection end (4.6/5.4s) was displayed
   instead of the incast batch's (~2.057s). injection_end participates in
   no metric or claim; the package computes it over incast rounds only and
   the timestamp cross-check passes 30/30 after the fix.
