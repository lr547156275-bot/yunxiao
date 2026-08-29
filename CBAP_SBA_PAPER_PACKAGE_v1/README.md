# CBAP_SBA_PAPER_PACKAGE_v1

Self-contained, independently recomputable data package for the CBAP-SBA
paper. Repo: github.com/lr547156275-bot/yunxiao @ cbap-queue-delay-credit;
raw traces: Release evidence-2026-08 (not duplicated here; SHAs in
00_RUN_INVENTORY.csv and matrix_manifest in the repo).

00_CODE_PROVENANCE.md      code/binary SHAs, commits, patch list
00_RUN_INVENTORY.csv       every run: config/result paths, SHAs, status
01_METRIC_DEFINITIONS.md   frozen CCT/BCT/FCT/injection_span + sources
02_TIMESTAMP_CROSSCHECK.csv three-timestamp ordering check (30/30 OK)
03_MAIN_RESULTS_LONG.csv   S1-S6 x 5 algorithms, all metrics, abs+rel
04_PER_FLOW_RESULTS.csv    1705 per-flow rows across the matrix
05_CONTROL_TIMELINE.csv    S3 CBAP control timeline (30k events)
05b_S6_PER_LINK_QUEUES.csv S6 bottlenecks reported per link
06_PARAMETER_BOOK.csv      every parameter: value, range, source, frozen
07_TUNING_RESULTS.csv      every tried point (28), protocol note
08_ABLATION_RESULTS.csv    D1/D2/D3/D4v1(INVALID)/D4v2
09_ROBUSTNESS_RESULTS.csv  14 robustness axes incl. not-run markers
10_CLAIMS_EVIDENCE.csv     8 paper claims with evidence pointers
11_CORRECTIONS_AND_PROVENANCE.md  10 recorded corrections/retractions
12_MISSING_EXPERIMENTS.md  what was NOT run (do not cite)
PAPER_INPUT.md             verified-only paper summary
FIGURE_DATA/               csv per figure   FIGURES/ pdf+svg+png
FIGURE_SCRIPTS/make_figures.py  regenerates all figures from FIGURE_DATA
SHA256SUMS                 checksums of every file in this package
