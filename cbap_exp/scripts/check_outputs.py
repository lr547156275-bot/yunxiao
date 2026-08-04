#!/usr/bin/env python3
import argparse
import csv
import json
import math
import os
import sys

CBAP = {"independent_min_grant", "cbap_init_only",
        "cbap_rate_only", "cbap_full"}


def fail(message):
    print("INVALID " + message, file=sys.stderr)
    raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    parser.add_argument("--allow-no-complete-flag", action="store_true")
    args = parser.parse_args()
    run = os.path.abspath(args.run_dir)
    required = ("run_meta.json", "exit_status.txt", "flow_summary.csv",
                "round_summary.csv", "feedback_summary.csv",
                "queue_summary.csv", "rate_summary.csv",
                "control_summary.csv", "result.json")
    for name in required:
        if not os.path.isfile(os.path.join(run, name)):
            fail("missing " + name)
    if not args.allow_no_complete_flag and not os.path.isfile(
            os.path.join(run, "completed.flag")):
        fail("missing completed.flag")
    meta = json.load(open(os.path.join(run, "run_meta.json")))
    if int(open(os.path.join(run, "exit_status.txt")).read().strip()) != 0:
        fail("nonzero exit")
    result = json.load(open(os.path.join(run, "result.json")))
    if not result["all_flows_completed"]:
        fail("incomplete flow")
    for key, value in result.items():
        if isinstance(value, float) and not math.isfinite(value):
            fail("nonfinite " + key)
    expected = int(open(os.path.join(run, "flow.txt")).readline())
    if result["flow_count"] != expected:
        fail("flow count")
    if meta["algorithm"] in CBAP:
        for name in ("cbap_port_summary.csv", "cbap_admission.csv",
                     "cbap_rate_transitions.csv", "cbap_flow_state.csv",
                     "cbap_control_overhead.csv"):
            path = os.path.join(run, name)
            if not os.path.isfile(path) or os.path.getsize(path) == 0:
                fail("missing CBAP output " + name)
        if result["capacity_violations"] or result["credit_violations"]:
            fail("CBAP audit violation")
    if int(meta["seed"]) == 1:
        trace = os.path.join(run, "cbap_packet_trace.csv")
        compressed = trace + ".gz"
        if not ((os.path.isfile(trace) and os.path.getsize(trace) > 200) or
                (os.path.isfile(compressed) and
                 os.path.getsize(compressed) > 100)):
            fail("missing bounded seed=1 packet trace")
        log_path = os.path.join(run, "stdout.log")
        if os.path.isfile(log_path):
            log = open(log_path, errors="replace").read()
            if "CBAP_PACKET_TRACE_TRUNCATED" in log:
                fail("seed=1 packet trace truncated")
    print("VALID " + run)


if __name__ == "__main__":
    main()
