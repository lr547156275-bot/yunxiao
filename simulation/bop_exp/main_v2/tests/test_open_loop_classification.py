#!/usr/bin/env python3
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
reg = {r["algorithm_name"]: r for r in csv.DictReader(
    open(ROOT / "config/algorithm_registry.csv"))}
configured = reg["open_loop_pfc_configured"]
disabled = reg["open_loop_pfc_disabled"]
assert configured["display_name"] == "open_loop_no_endhost_cc"
assert configured["baseline_class"] == "open_loop_reference"
assert configured["formal_main"] == "0"
assert configured["best_formal_cc_eligible"] == "0"
assert configured["cc_mode"] == disabled["cc_mode"] == "0"
assert configured["pfc_configured"] == "1"
assert disabled["pfc_configured"] == "0"
rows = list(csv.DictReader(
    open(ROOT / "config/open_loop_reference_manifest.csv")))
assert len(rows) == 45
assert {r["algorithm"] for r in rows} == {"open_loop_pfc_configured"}
assert all(r["formal_cc_baseline"] == "false" for r in rows)
print("PASS open-loop classification=reference only")
