#!/usr/bin/env python3
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
eligible = {"dctcp", "dcqcn", "timely", "hpcc_int"}
rows = list(csv.DictReader(
    open(ROOT / "analysis/best_cc_baseline_comparison.csv")))
assert len(rows) == 15
assert {r["best_formal_cc_baseline"] for r in rows} <= eligible
pairwise = list(csv.DictReader(
    open(ROOT / "analysis/pairwise_bop_vs_cc.csv")))
assert pairwise
assert {r["baseline_algorithm"] for r in pairwise} <= eligible
tradeoff = list(csv.DictReader(open(ROOT / "analysis/open_loop_tradeoff.csv")))
assert len(tradeoff) == 15
assert all(r["reference_name"] == "open_loop_no_endhost_cc"
           for r in tradeoff)
print("PASS best formal CC selection excludes open-loop")
