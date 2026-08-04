#!/usr/bin/env python3
import argparse
import csv
import gzip
import json
import math
import os
import sys

from closlib import CONFIG, digest, input_hashes, read_csv


def read_maybe_gzip(path):
    plain = path
    gz = path + ".gz"
    if os.path.exists(plain):
        with open(plain, newline="") as handle:
            return list(csv.DictReader(handle))
    if os.path.exists(gz):
        with gzip.open(gz, "rt", newline="") as handle:
            return list(csv.DictReader(handle))
    return []


def validate(run_dir, require_flag=True):
    errors = []
    required = ("run_meta.json", "exit_status.txt", "flow_summary.csv",
                "round_summary.csv", "group_round_summary.csv",
                "controller_summary.csv", "feedback_summary.csv",
                "pfc_events.csv", "run_metrics.csv", "per_link_metrics.csv",
                "collective_metrics.csv")
    for name in required:
        if not os.path.exists(os.path.join(run_dir, name)):
            errors.append("missing " + name)
    if require_flag and not os.path.exists(
            os.path.join(run_dir, "completed.flag")):
        errors.append("missing completed.flag")
    if errors:
        return errors
    meta = json.load(open(os.path.join(run_dir, "run_meta.json")))
    try:
        status = int(open(os.path.join(run_dir, "exit_status.txt")).read())
    except Exception:
        status = -1
    if status != 0 or meta.get("exit_status") != 0:
        errors.append("nonzero exit status")
    try:
        if input_hashes(run_dir) != meta["input_hashes"]:
            errors.append("input hash mismatch")
    except Exception as exc:
        errors.append("input hash check failed: %s" % exc)
    flows = read_csv(os.path.join(run_dir, "flow_summary.csv"))
    rounds = read_csv(os.path.join(run_dir, "round_summary.csv"))
    groups = read_csv(os.path.join(run_dir, "group_round_summary.csv"))
    schedule = read_csv(os.path.join(run_dir, "collective_schedule.csv"))
    expected_flows = int(open(os.path.join(run_dir, "flow.txt")).readline())
    expected_rounds = int(open(os.path.join(run_dir, "rounds.txt")).readline())
    if len(flows) != expected_flows:
        errors.append("flow completion count %d != %d" %
                      (len(flows), expected_flows))
    if len(rounds) != expected_rounds:
        errors.append("round count %d != %d" %
                      (len(rounds), expected_rounds))
    if len(groups) != len(schedule):
        errors.append("group count %d != %d" % (len(groups), len(schedule)))
    if any(row.get("completed") != "1" for row in flows):
        errors.append("incomplete flow")
    by_group = {int(row["group_id"]): row for row in groups}
    for item in schedule:
        group_id = int(item["group_id"])
        if group_id not in by_group:
            continue
        row = by_group[group_id]
        release = float(row["common_release_time"])
        barrier = float(row["barrier_completion_time"])
        if not (barrier >= release > 0):
            errors.append("invalid barrier group %d" % group_id)
        predecessor = int(item["predecessor_group_id"])
        if predecessor >= 0 and predecessor in by_group:
            prior = float(by_group[predecessor]["barrier_completion_time"])
            if release + 1e-15 < prior:
                errors.append("cross-round overlap group %d" % group_id)
    numeric_files = ("flow_summary.csv", "round_summary.csv",
                     "group_round_summary.csv", "run_metrics.csv",
                     "per_link_metrics.csv", "collective_metrics.csv")
    for name in numeric_files:
        text = open(os.path.join(run_dir, name), errors="replace").read().lower()
        if "nan" in text or "inf" in text:
            errors.append("NaN/Inf in " + name)
    log_candidates = ("run.log", "run.log.gz")
    for name in log_candidates:
        path = os.path.join(run_dir, name)
        if not os.path.exists(path):
            continue
        opener = gzip.open if name.endswith(".gz") else open
        with opener(path, "rt", errors="replace") as handle:
            if "LOG_TRUNCATED" in handle.read():
                errors.append("log truncated")
    if meta["algorithm"] == "bop_qb":
        group_decisions = read_csv(os.path.join(
            run_dir, "bop_multilink_group_decisions.csv"))
        link_decisions = read_csv(os.path.join(
            run_dir, "bop_multilink_link_constraints.csv"))
        plans = read_maybe_gzip(os.path.join(run_dir, "flow_plan.csv"))
        if len(group_decisions) != len(schedule):
            errors.append("BOP multilink group decision count mismatch")
        if not link_decisions:
            errors.append("missing BOP link decisions")
        for row in group_decisions + link_decisions:
            for key in ("formula_valid", "capacity_valid",
                        "credit_constraint_valid"):
                if row.get(key) != "1":
                    errors.append("%s false in group %s" %
                                  (key, row.get("group_id")))
                    break
        if len(plans) != expected_rounds:
            errors.append("BOP flow plan count mismatch")
    return sorted(set(errors))


def manifest_rows():
    return read_csv(os.path.join(CONFIG, "run_manifest.csv"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pre-complete", action="store_true")
    parser.add_argument("--list-invalid")
    parser.add_argument("--seeds", default="1,2,3")
    parser.add_argument("run_dir", nargs="?")
    args = parser.parse_args()
    if args.list_invalid:
        wanted = set(int(value) for value in args.seeds.split(","))
        for row in manifest_rows():
            if int(row["seed"]) not in wanted:
                continue
            path = os.path.join(args.list_invalid, row["run_id"])
            if validate(path, True):
                print(row["run_id"])
        return
    if not args.run_dir:
        parser.error("run_dir is required")
    errors = validate(os.path.abspath(args.run_dir),
                      require_flag=not args.pre_complete)
    if errors:
        for error in errors:
            print("FAIL " + error, file=sys.stderr)
        raise SystemExit(1)
    print("PASS " + os.path.abspath(args.run_dir))


if __name__ == "__main__":
    main()

