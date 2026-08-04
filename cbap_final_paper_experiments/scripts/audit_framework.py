#!/usr/bin/env python3
"""Static audit of manifests, frozen modes, hashes and optional preflight runs."""
import argparse
import csv
import hashlib
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(ROOT, ".."))
EXPECTED = {"single_bottleneck.csv": 560, "release_skew.csv": 420,
            "multibottleneck.csv": 56, "clos.csv": 140,
            "randomized_robustness.csv": 210, "ablations.csv": 22,
            "all_runs.csv": 1408, "preflight.csv": 7}
MODES = {"dctcp": 8, "dcqcn": 1, "timely": 7, "hpcc_int": 3,
         "bop_qb": 15, "independent_min_grant": 20,
         "cbap_full_v13_ratefloor_fix": 25, "cbap_init_only": 21,
         "cbap_rateonly_v11": 22, "cbap_full_v14_stable_handoff": 26,
         "cbap_full_v15_guarded_delegation": 27}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""): h.update(block)
    return h.hexdigest()


def fail(message, errors):
    errors.append(message); print("FAIL " + message, file=sys.stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-results", action="store_true")
    args = parser.parse_args(); errors = []
    gate = os.path.join(REPO, "cbap_final_metric_pipeline", "reports",
                        "metric_pipeline_selftest.md")
    if not os.path.isfile(gate) or "METRIC_PIPELINE_PASS" not in open(gate).read():
        fail("metric gate", errors)
    master = []
    for name, count in EXPECTED.items():
        path = os.path.join(ROOT, "manifests", name)
        rows = list(csv.DictReader(open(path))) if os.path.isfile(path) else []
        if len(rows) != count: fail("%s count %d != %d" % (name, len(rows), count), errors)
        if name == "all_runs.csv": master = rows
        for row in rows:
            if int(row["cc_mode"]) != MODES[row["algorithm"]]:
                fail("mode mismatch " + row["run_id"], errors)
            case = os.path.join(ROOT, row["case_dir"])
            if not os.path.isdir(case): fail("missing case " + row["case_dir"], errors); continue
            for file_name, field in (("config.txt", "config_hash"),
                                     ("flow.txt", "flow_hash")):
                if sha(os.path.join(case, file_name)) != row[field]:
                    fail("hash mismatch %s %s" % (row["run_id"], file_name), errors)
    if len({r["run_id"] for r in master}) != len(master): fail("duplicate run_id", errors)
    formal = set(MODES) - {"cbap_init_only", "cbap_rateonly_v11",
                           "cbap_full_v14_stable_handoff",
                           "cbap_full_v15_guarded_delegation"}
    for row in master:
        if row["experiment_family"] != "ablation" and row["algorithm"] not in formal:
            fail("nonformal algorithm in main matrix", errors)
    grouped = {}
    for row in master:
        if row["experiment_family"] == "ablation": continue
        key = (row["experiment_family"], row["scenario_id"], row["seed"])
        grouped.setdefault(key, set()).add((row["flow_hash"], row["path_hash"],
                                            row["random_input_hash"]))
    if any(len(values) != 1 for values in grouped.values()):
        fail("cross-algorithm input mismatch", errors)
    random_groups = {}
    for row in master:
        if row["experiment_family"] == "randomized" and row["algorithm"] == "dcqcn":
            base = re.sub(r"_random_seed\d+$", "", row["scenario_id"])
            random_groups.setdefault(base, set()).add(row["random_input_hash"])
    if len(random_groups) != 6 or any(len(v) != 5 for v in random_groups.values()):
        fail("randomized seed effectiveness", errors)
    if args.preflight_results:
        rows = list(csv.DictReader(open(os.path.join(ROOT, "manifests", "preflight.csv"))))
        for row in rows:
            run = os.path.join(ROOT, "preflight", "runs", row["run_id"])
            if not os.path.isfile(os.path.join(run, "completed.flag")):
                fail("preflight incomplete " + row["run_id"], errors)
    if errors: raise SystemExit(1)
    print("FRAMEWORK_STATIC_PASS manifests=1408 preflight=7 randomized_seed_groups=6")


if __name__ == "__main__": main()
