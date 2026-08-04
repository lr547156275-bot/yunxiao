#!/usr/bin/env python3
import csv
import gzip
import json
import os
import shutil
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SIM = os.path.abspath(os.path.join(ROOT, "..", ".."))
MAIN = os.path.join(SIM, "bop_exp", "main_v1")
CASES = ("msg_64k_n16_g50", "msg_256k_n16_g50", "n32_64k_g50")


def rows(path):
    if os.path.exists(path):
        with open(path, newline="") as handle:
            return list(csv.DictReader(handle))
    if os.path.exists(path + ".gz"):
        with gzip.open(path + ".gz", "rt", newline="") as handle:
            return list(csv.DictReader(handle))
    raise AssertionError("missing " + path)


def rewrite(source, destination):
    output = []
    with open(source) as handle:
        for line in handle:
            if line.startswith("CRFM_MIN_FREE_GB "):
                output.append("CRFM_MIN_FREE_GB 0\n")
            else:
                output.append(line)
    with open(destination, "w") as handle:
        handle.writelines(output)


def prepare(case):
    reference = os.path.join(MAIN, "runs", case, "bop_qb", "seed_1")
    target = os.path.join(ROOT, "single_bottleneck_regression", case)
    os.makedirs(target, exist_ok=True)
    for name in ("topology.txt", "flow.txt", "rounds.txt",
                 "fixed_paths.txt", "trace.txt", "scenario_meta.json"):
        shutil.copy2(os.path.join(reference, name), os.path.join(target, name))
    rewrite(os.path.join(reference, "config.txt"),
            os.path.join(target, "config.txt"))
    return target


def numeric_map(rows_value, keys, value):
    return {tuple(row[key] for key in keys): float(row[value])
            for row in rows_value}


def check_case(case):
    ref = os.path.join(MAIN, "runs", case, "bop_qb", "seed_1")
    cur = os.path.join(ROOT, "single_bottleneck_regression", case)
    problems = []
    old_groups, new_groups = rows(os.path.join(
        ref, "group_round_summary.csv")), rows(os.path.join(
        cur, "group_round_summary.csv"))
    old_rct = numeric_map(old_groups, ("group_id",), "group_rct")
    new_rct = numeric_map(new_groups, ("group_id",), "group_rct")
    if old_rct.keys() != new_rct.keys() or any(
            abs(old_rct[key] - new_rct[key]) * 1e9 > 1
            for key in old_rct):
        problems.append("group RCT differs by >1ns")
    old_queue = max(float(row["queue_bytes"]) for row in rows(
        os.path.join(ref, "selected_link_timeseries.csv")))
    new_queue = max(float(row["queue_bytes"]) for row in rows(
        os.path.join(cur, "selected_link_timeseries.csv")))
    if abs(old_queue - new_queue) > 1:
        problems.append("queue max differs by >1B")
    if sum(int(row["group_ecn_marks"]) for row in old_groups) != \
            sum(int(row["group_ecn_marks"]) for row in new_groups):
        problems.append("ECN differs")
    old_dec = rows(os.path.join(ref, "bop_qb_group_decisions.csv"))
    new_dec = rows(os.path.join(cur, "bop_qb_group_decisions.csv"))
    for field in ("group_credit_bytes", "total_allocated_credit_bytes"):
        if [row[field] for row in old_dec] != [row[field] for row in new_dec]:
            problems.append(field + " differs")
    old_plan = rows(os.path.join(ref, "flow_plan.csv"))
    new_plan = rows(os.path.join(cur, "flow_plan.csv"))
    for field in ("qb_base_rate_bps", "selected_rate_bps",
                  "qb_credit_bytes"):
        if [row[field] for row in old_plan] != [row[field] for row in new_plan]:
            problems.append(field + " differs")
    def order(path):
        values = rows(path)
        return [row["flow_id"] for row in sorted(
            values, key=lambda row: (float(row["finish_time"]),
                                     int(row["flow_id"])))]
    if order(os.path.join(ref, "flow_summary.csv")) != order(os.path.join(
            cur, "flow_summary.csv")):
        problems.append("flow completion order differs")
    return problems


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("prepare", "check"):
        raise SystemExit("usage: regression.py prepare|check CASE")
    if sys.argv[2] not in CASES:
        raise SystemExit("unknown regression case")
    if sys.argv[1] == "prepare":
        print(prepare(sys.argv[2]))
    else:
        issues = check_case(sys.argv[2])
        if issues:
            for issue in issues:
                print("FAIL %s: %s" % (sys.argv[2], issue))
            raise SystemExit(1)
        print("PASS " + sys.argv[2])

