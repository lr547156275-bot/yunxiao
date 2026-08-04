#!/usr/bin/env python3
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rows = list(csv.DictReader(open(ROOT / "config/main_manifest.csv")))
assert len(rows) == 273
sections = Counter(row["section"] for row in rows)
assert sections == {"main": 225, "ablation": 30, "wire_fairness": 18}
assert len({row["run_id"] for row in rows}) == 273
assert "pfc_only" not in {row["algorithm"] for row in rows}
assert "open_loop_pfc_configured" not in {row["algorithm"] for row in rows}
scenarios = list(csv.DictReader(open(ROOT / "config/main_scenarios.csv")))
assert len(scenarios) == 15
print("PASS main_v2 manifest 273=225+30+18")
