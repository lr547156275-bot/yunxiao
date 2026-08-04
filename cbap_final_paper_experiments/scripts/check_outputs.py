#!/usr/bin/env python3
"""Validate a finished run and its immutable manifest identity."""
import argparse
import csv
import hashlib
import json
import math
import os
import sys


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""): h.update(block)
    return h.hexdigest()


def fail(message):
    print("INVALID " + message, file=sys.stderr); raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir"); parser.add_argument("--pre-complete", action="store_true")
    args = parser.parse_args(); run = os.path.abspath(args.run_dir)
    required = ("manifest.json", "run_meta.json", "scenario_meta.json",
                "config.txt", "flow.txt", "rounds.txt", "flow_plan.csv",
                "flow_summary.csv", "round_summary.csv", "incumbent_summary.csv",
                "queue_summary.csv", "rate_summary.csv", "scope_summary.csv",
                "control_summary.csv", "result_full_work.json",
                "flow_outcome_ledger.csv", "metric_provenance.json",
                "exit_status.txt", "stdout.log")
    for name in required:
        if not os.path.isfile(os.path.join(run, name)): fail("missing " + name)
    if not args.pre_complete and not os.path.isfile(os.path.join(run, "completed.flag")):
        fail("missing completed.flag")
    if int(open(os.path.join(run, "exit_status.txt")).read().strip()): fail("nonzero exit")
    manifest = json.load(open(os.path.join(run, "manifest.json")))
    meta = json.load(open(os.path.join(run, "run_meta.json")))
    result = json.load(open(os.path.join(run, "result_full_work.json")))
    if int(meta.get("cc_mode", -1)) != int(manifest["cc_mode"]): fail("CC_MODE mismatch")
    if meta.get("algorithm_name") != manifest["algorithm"]: fail("algorithm mismatch")
    for name, expected in manifest.get("input_hashes", {}).items():
        path = os.path.join(run, name)
        if not os.path.isfile(path) or sha(path) != expected: fail("input hash " + name)
    if result.get("byte_conservation_valid") is not True: fail("byte conservation")
    # Formal runs use a common observation horizon.  A long-lived incumbent
    # may be right-censored; the corrected collector must preserve its
    # delivered/remaining bytes.  Preflight remains stricter and requires all
    # flows to finish.
    if not result.get("all_newcomers_completed"): fail("not all newcomers completed")
    if manifest.get("experiment_family") == "preflight" and not result.get("all_flows_completed"):
        fail("preflight not all flows completed")
    if not result.get("all_flows_completed") and result.get(
            "censored_makespan_lower_bound_us") in (None, ""):
        fail("missing censored makespan lower bound")
    if result.get("capacity_violation_count", 0): fail("planner capacity violation")
    # Violations in formal runs are measured adverse outcomes, not grounds for
    # deleting data.  Preflight is the implementation sanity gate and remains
    # strict; formal analysis applies the preregistered zero-violation rule when
    # classifying a scenario as Pareto-positive.
    if manifest.get("experiment_family") == "preflight" and \
       manifest.get("algorithm") == "cbap_full_v13_ratefloor_fix":
        if result.get("applied_capacity_violation_count", 0): fail("CBAP applied capacity violation")
        if result.get("credit_violation_count", 0): fail("CBAP credit violation")
        if result.get("pacing_violation_count", 0): fail("CBAP pacing violation")
    if meta.get("log_truncated"): fail("log truncated")
    for value in result.values():
        if isinstance(value, float) and not math.isfinite(value): fail("NaN/Inf")
    ledger = list(csv.DictReader(open(os.path.join(run, "flow_outcome_ledger.csv"))))
    planned = sum(1 for line in open(os.path.join(run, "flow.txt")) if line.split()) - 1
    if len(ledger) != planned: fail("flow ledger count")
    if sum(int(float(row.get("planned_bytes", 0))) for row in ledger) != \
       sum(int(float(row.get("delivered_bytes_final", 0))) +
           int(float(row.get("remaining_bytes_final", 0))) for row in ledger):
        fail("ledger byte conservation")
    print("VALID " + run)


if __name__ == "__main__": main()
