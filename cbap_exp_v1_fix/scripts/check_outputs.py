#!/usr/bin/env python3
import argparse
import csv
import gzip
import json
import math
import os
import sys


CBAP = {"independent_min_grant", "cbap_init_only",
        "cbap_rate_only", "cbap_full"}


def existing(path):
    """Return raw or post-success compressed detailed output path."""
    if os.path.isfile(path) and os.path.getsize(path):
        return path
    if os.path.isfile(path + ".gz") and os.path.getsize(path + ".gz"):
        return path + ".gz"
    return ""


def csv_rows(path):
    actual = existing(path)
    if not actual:
        return []
    opener = gzip.open if actual.endswith(".gz") else open
    with opener(actual, "rt", newline="") as stream:
        return list(csv.DictReader(stream))


def fail(message):
    print("INVALID " + message, file=sys.stderr)
    raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    parser.add_argument("--allow-no-complete-flag", action="store_true")
    args = parser.parse_args()
    run = os.path.abspath(args.run_dir)
    required = (
        "run_meta.json", "exit_status.txt", "flow_summary.csv",
        "round_summary.csv", "feedback_summary.csv", "queue_summary.csv",
        "rate_summary.csv", "control_summary.csv", "result.json",
    )
    for name in required:
        if not os.path.isfile(os.path.join(run, name)):
            fail("missing " + name)
    if not args.allow_no_complete_flag and not os.path.isfile(
            os.path.join(run, "completed.flag")):
        fail("missing completed.flag")
    meta = json.load(open(os.path.join(run, "run_meta.json")))
    if int(open(os.path.join(run, "exit_status.txt")).read().strip()):
        fail("nonzero exit")
    result = json.load(open(os.path.join(run, "result.json")))
    if not result.get("all_flows_completed"):
        fail("incomplete flow")
    if result.get("log_truncated"):
        fail("log truncated")
    for key, value in result.items():
        if isinstance(value, float) and not math.isfinite(value):
            fail("nonfinite " + key)
    if meta["algorithm"] in CBAP:
        for name in (
                "cbap_port_summary.csv", "cbap_admission.csv",
                "cbap_rate_transitions.csv", "cbap_flow_state.csv",
                "cbap_control_overhead.csv", "cbap_tx_events.csv"):
            if not existing(os.path.join(run, name)):
                fail("missing CBAP output " + name)
        rows = csv_rows(os.path.join(run, "cbap_flow_state.csv"))
        required_fields = {
            "admission_enter_ns", "admission_exit_ns", "first_data_tx_ns",
            "first_post_release_sample_ns",
            "first_complete_fresh_feedback_ns", "initial_admit_rate_bps",
            "actual_admission_mean_rate_bps",
            "bytes_sent_before_fresh_feedback",
            "ordinary_rate_updates_during_admission",
            "emergency_rate_updates_during_admission",
            "credit_gate_enter_ns", "credit_gate_exit_ns",
            "credit_remaining_at_admission_exit",
            "tracking_actual_rate_bps", "tracking_current_rate_bps",
            "tracking_base_rate_bps", "pacing_violations",
        }
        if not rows or not required_fields.issubset(rows[0]):
            fail("missing v1 semantic fields")
    print("VALID " + run)


if __name__ == "__main__":
    main()
