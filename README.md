# CBAP-SBA: Admission-Planned Congestion Control for RDMA Incast

ns-3 implementation and full experimental evidence for **CBAP-SBA**, a
proactive congestion-control scheme for RoCE/RDMA datacenter incast.
Instead of discovering congestion reactively through queue buildup,
CBAP-SBA treats a synchronized incast batch as a *known event*: it plans
rates at admission time, explicitly migrates capacity from pre-existing
flows to the new batch (and back on completion, ~500x faster than DCQCN's
self-recovery), pins steady state at link capacity, and closes the final
utilization gap with a small **leased, prediction-vetoed headroom top-up**
(the D4v2 controller).

This repository is a fork of the [HPCC SIGCOMM'19 simulator](https://rmiao.github.io/publications/hpcc-li.pdf)
(see *Upstream* below), which provides the ns-3 base and the DCQCN, DCTCP,
TIMELY, HPCC, PFC/ECN and shared-buffer switch implementations used as
baselines.

## Headline results (5 algorithms x 6 scenarios, `matrix_report.md`)

| | DCQCN | DCTCP | TIMELY | HPCC | CBAP-SBA |
|---|---|---|---|---|---|
| Scenarios fastest (CCT) | 1 (tie) | 0 | 0 | 0 | **5 (+1 tie)** |
| Queue-budget (838.86 us) violations | 4/6 | 4/6 | 4/6 | 4/6 | **0/6** |
| Worst-link queue p99 | up to 1.27 MB | up to 1.27 MB | up to 1.08 MB | 14-19 KB* | **<= 38 KB** |
| Max queuing delay | ~1.02 ms | ~1.02 ms | ~1.02 ms | ~1.04 ms | **16-39 us** |

\* HPCC's steady-state p99 is low, but its batch-release burst still peaks
at 1.30 MB and it is the slowest algorithm in 4 of 6 scenarios.

A 21-point baseline **parameter sweep** (`figdata/frontier_s3.csv`) shows no
swept configuration of any baseline enters CBAP-SBA's (completion x queue)
region — `FRONTIER_DOMINANCE_HOLDS`. The fastest reachable baseline point
is "ECN effectively disabled", and is still 0.58% slower at 64x the queue.
A sensitivity annex (`SENSITIVITY_ANNEX.md`) shows that on a shallow-buffer
switch every baseline triggers 438-11,548 PFC pauses per batch while
CBAP-SBA's execution is byte-identical to the deep-buffer run.

## Repository layout

```
simulation/                    ns-3 tree (waf, python2)
  scratch/third.cc             experiment harness (config-file driven)
  src/point-to-point/model/    rdma-hw.cc (controller), cbap-sba.cc (admission)
  experiment/scheme1_sba/      all cell configs, reports (*.md), summaries
    matrix_report.md           final 30-cell matrix tables
    final_results.csv          one row per matrix cell
    figdata/                   per-figure CSVs (incl. frontier_s3.csv)
    matrix_manifest.txt        SHA-256 of binary, configs, scenario files
    SENSITIVITY_ANNEX.md       shallow-buffer / ECN-threshold annex
    ZONE_COVERAGE_STRESS.md    zone state-machine stress + design envelope
tools/                         cell generators, serial runners, extractors
tools/patches/                 every source patch script + unit tests
CHECKPOINT_PROVENANCE/         pre-patch source backups, cleanup manifests
*_logs/                        per-round supervisor and cell logs
traffic_gen/, analysis/        upstream HPCC tooling
```

## Reproducing

The simulation is **deterministic** (no random variates on reachable paths;
verified bit-identical across seeds), so every number in the reports is
exactly reproducible from the committed configs.

```bash
# environment: ubuntu 20.04, g++-7, python2.7
cd simulation && python2 ./waf configure && python2 ./waf build -j2

# one cell:
cd experiment/scheme1_sba
LD_LIBRARY_PATH=../../build ../../build/scratch/third mx_s3_cbapsba.txt

# full 30-cell matrix (serial, ~13 h) + extraction:
bash /path/to/repo/tools/run_matrix30.sh        # expects /work = repo root
python3 /path/to/repo/tools/matrix_metrics.py
```

Raw traces (`*_out/`, ~13 GB) are git-ignored; the complete raw outputs
backing every report are attached to the GitHub Release
**`evidence-2026-08`** as split tarballs (see release notes for layout).

## Provenance model

Every experimental round followed the same discipline: pre-registered
expectations, atomic anchored source patches (`tools/patches/`), byte-level
twin regressions proving instrumentation neutrality, SHA manifests, and
honest labels (`INVALID_OVERBOOST_POLICY`, `BOUNDARY_PROBE`, ...) for
negative results — which are retained, not deleted.

## Known limitations (stated in the reports)

- Single seed (justified by proven determinism); perturbation study not run.
- Single-hop bottleneck topology (S6 is dual-bottleneck, still single-hop);
  multi-hop PFC head-of-line effects unmeasured.
- Concurrent controlled-flow count bounded (~94) by MIN_RATE floor
  feasibility — a documented admission envelope.
- TIMELY's T_LOW/T_HIGH are not exposed by the harness config parser; its
  sweep covers RATE_AI only.
- Grant budgets retain a ~4.6% wire/payload domain mix in the startup
  transient (steady-state control is domain-correct); documented as debt.

## Upstream

This fork builds on the HPCC simulator by Rui Miao et al.:
[HPCC: High Precision Congestion Control (SIGCOMM'19)](https://rmiao.github.io/publications/hpcc-li.pdf),
with HPCC-PINT updates ([PINT, SIGCOMM'20](https://liyuliang001.github.io/publications/pint.pdf)).
The upstream project page is <https://hpcc-group.github.io/>. Upstream
tooling under `traffic_gen/` and `analysis/` is unchanged; for questions
about the base simulator contact the upstream authors.

## License

To be chosen by the author before publication (upstream simulator license
terms apply to inherited code).
