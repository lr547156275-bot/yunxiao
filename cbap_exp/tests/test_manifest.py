#!/usr/bin/env python3
import csv
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
rows = list(csv.DictReader(open(os.path.join(
    ROOT, "config", "run_manifest.csv"))))
assert len(rows) == 147
assert len(set(row["run_id"] for row in rows)) == 147
assert set(int(row["cc_mode"]) for row in rows) == {1, 3, 15, 20, 21, 22, 23}
assert set(int(row["seed"]) for row in rows) == {1, 2, 3}
for row in rows:
    case = os.path.join(ROOT, "cases", row["scenario"], row["subcase"])
    for name in ("topology.txt", "flow.txt", "trace.txt", "config.txt",
                 "rounds.txt", "controlled_links.txt",
                 "controlled_paths.txt", "group_schedule.txt",
                 "scenario_meta.json", "input_hashes.json"):
        assert os.path.isfile(os.path.join(case, name)), (case, name)
    assert json.load(open(os.path.join(case, "scenario_meta.json")))\
        ["fixed_path"] is True
print("PASS manifest 147")
