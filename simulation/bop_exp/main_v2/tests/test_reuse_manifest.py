#!/usr/bin/env python3
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rows = list(csv.DictReader(open(ROOT / "config/reuse_manifest.csv")))
assert len(rows) == 273
required = {"topology_hash", "flow_hash", "rounds_hash",
            "fixed_path_hash", "source_hash", "algorithm_config_hash",
            "packet_payload_bytes", "ecn_threshold_config",
            "pfc_threshold_config", "link_rate", "ack_config", "cc_mode",
            "reuse_allowed", "reuse_reject_reason"}
assert required <= set(rows[0])
assert all(r["reuse_allowed"] == "true" for r in rows), [
    r["run_id"] for r in rows if r["reuse_allowed"] != "true"][:5]
assert all(r["source_run"].startswith("bop_exp/main_v1/runs/")
           for r in rows)
print("PASS reuse manifest validated=273")
