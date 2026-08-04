#!/usr/bin/env python3
"""Prepare exactly one manifest row in an isolated run directory."""
import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(ROOT, ".."))

OUTPUTS = {
    "FLOW_SUMMARY_FILE": "flow_summary.csv",
    "ROUND_SUMMARY_FILE": "round_summary.csv",
    "FEEDBACK_SUMMARY_FILE": "feedback_summary.csv",
    "CONTROLLER_SUMMARY_FILE": "controller_summary.csv",
    "GROUP_ROUND_SUMMARY_FILE": "group_round_summary.csv",
    "FLOW_PLAN_FILE": "flow_plan.csv",
    "LINK_TIMESERIES_FILE": "selected_link_timeseries.csv",
    "SELECTED_FLOW_TIMESERIES_FILE": "selected_flow_timeseries.csv",
    "PFC_OUTPUT_FILE": "pfc_events.csv",
    "BOP_QB_GROUP_DECISIONS_FILE": "bop_qb_group_decisions.csv",
    "BOP_MULTILINK_GROUP_DECISIONS_FILE": "bop_multilink_group_decisions.csv",
    "BOP_MULTILINK_LINK_CONSTRAINTS_FILE": "bop_multilink_link_constraints.csv",
    "CBAP_PORT_SUMMARY_FILE": "cbap_port_summary.csv",
    "CBAP_ADMISSION_FILE": "cbap_admission.csv",
    "CBAP_RATE_TRANSITION_FILE": "cbap_rate_transitions.csv",
    "CBAP_FLOW_STATE_FILE": "cbap_flow_state.csv",
    "CBAP_CONTROL_OVERHEAD_FILE": "cbap_control_overhead.csv",
    "CBAP_SCOPE_SUMMARY_FILE": "scope_summary.csv",
    "CBAP_SCOPE_LINK_FILE": "scope_link_summary.csv",
    "CBAP_APPLIED_RATE_AUDIT_FILE": "applied_rate_audit.csv",
    "CBAP_TX_EVENT_FILE": "sender_tx_trace.csv",
    "CBAP_INCREASE_AUDIT_FILE": "increase_policy_events.csv",
    "FIXED_PATH_OUTPUT_FILE": "resolved_fixed_paths.csv",
}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rewrite(source, destination, updates):
    lines, seen = [], set()
    for line in open(source):
        words = line.split()
        key = words[0] if words and not words[0].startswith("#") else ""
        if key in updates:
            lines.append("%s %s\n" % (key, updates[key])); seen.add(key)
        else:
            lines.append(line)
    for key in sorted(set(updates) - seen):
        lines.append("%s %s\n" % (key, updates[key]))
    with open(destination, "w") as stream: stream.writelines(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest"); parser.add_argument("run_id")
    parser.add_argument("run_dir"); parser.add_argument("--min-free-gb", type=float, default=5)
    args = parser.parse_args()
    rows = {row["run_id"]: row for row in csv.DictReader(open(args.manifest))}
    if args.run_id not in rows: raise SystemExit("unknown run_id: " + args.run_id)
    row = rows[args.run_id]
    case = os.path.join(ROOT, row["case_dir"])
    run = os.path.abspath(args.run_dir); os.makedirs(run, exist_ok=True)
    if sha(os.path.join(case, "config.txt")) != row["config_hash"]:
        raise SystemExit("blueprint config hash mismatch")
    if sha(os.path.join(case, "flow.txt")) != row["flow_hash"]:
        raise SystemExit("blueprint flow hash mismatch")
    for name in os.listdir(case):
        source = os.path.join(case, name)
        if os.path.isfile(source) and name != "config.txt":
            shutil.copy2(source, os.path.join(run, name))
    mode = int(row["cc_mode"]); cbap = mode in (20, 21, 22, 23, 24, 25, 26, 27)
    updates = dict(OUTPUTS)
    updates.update({
        "CC_MODE": mode, "SIM_SEED": int(row["seed"]),
        "ALGORITHM": row["algorithm"], "SCENARIO": row["scenario_id"],
        "CBAP_ENABLE": int(cbap), "CBAP_VERSION": row["cbap_version"],
        "CBAP_SCOPE_POLICY": 1 if row["scope_policy"] ==
            "SHARED_BATCH_OVERSUBSCRIPTION" else 0,
        "CBAP_SCOPE_BASE_CC": 1,
        "CBAP_RATE_FLOOR_POLICY": int(row["rate_floor_policy"]),
        "CBAP_INCREASE_POLICY": 1 if mode in (23, 24, 25, 26, 27) else 0,
        "CBAP_INCREASE_FRACTION": .10,
        "CBAP_INCREASE_ABSOLUTE_BPS": 2000000000,
        "CBAP_RATEFLOOR_SEMANTIC_ZERO_TEST": 0,
        "CBAP_RATEFLOOR_SEMANTIC_ZERO_FLOW": 0,
        "CBAP_RATEFLOOR_SEMANTIC_ZERO_START_EPOCH": 0,
        "CBAP_RATEFLOOR_SEMANTIC_ZERO_END_EPOCH": 0,
        # third.cc requires a non-empty, bounded target for every seed-1 run.
        # /dev/null is intentional: this per-packet diagnostic is not part of
        # the preregistered output contract and would dominate disk usage.
        "CBAP_PACKET_TRACE_FILE": "/dev/null",
        "CBAP_PACKET_TRACE_MAX_MB": 64,
        "CBAP_TX_EVENT_FILE": "sender_tx_trace.csv" if cbap else "/dev/null",
        "CBAP_TX_TRACE_TRACKING_PACKETS": 4096,
        "CRFM_MIN_FREE_GB": args.min_free_gb,
        "FINAL_VALIDATION_ENABLE": 0,
    })
    if os.path.isfile(os.path.join(case, "multilink_links.txt")):
        updates.update({"BOP_MULTILINK_LINK_FILE": "multilink_links.txt",
                        "BOP_MULTILINK_PATH_FILE": "multilink_paths.txt",
                        "CBAP_LINK_FILE": "multilink_links.txt",
                        "CBAP_PATH_FILE": "multilink_paths.txt"})
    else:
        updates.update({"BOP_MULTILINK_LINK_FILE": "controlled_links.txt",
                        "BOP_MULTILINK_PATH_FILE": "controlled_paths.txt",
                        "CBAP_LINK_FILE": "controlled_links.txt",
                        "CBAP_PATH_FILE": "controlled_paths.txt"})
    rewrite(os.path.join(case, "config.txt"), os.path.join(run, "config.txt"), updates)
    immutable = [name for name in ("topology.txt", "flow.txt", "rounds.txt",
        "fixed_paths.txt", "controlled_links.txt", "controlled_paths.txt",
        "multilink_links.txt", "multilink_paths.txt", "group_schedule.txt",
        "collective_schedule.csv", "release_schedule.csv", "random_input.json",
        "scenario_meta.json", "trace.txt") if os.path.isfile(os.path.join(run, name))]
    hashes = {name: sha(os.path.join(run, name)) for name in immutable}
    manifest = dict(row)
    manifest.update({"algorithm_name": row["algorithm"], "input_hashes": hashes,
                     "blueprint_config_hash": row["config_hash"],
                     "prepared_config_hash": sha(os.path.join(run, "config.txt")),
                     "git_commit_at_prepare": subprocess.check_output(
                         ["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
                     "frozen_algorithm": row["algorithm"] ==
                         "cbap_full_v13_ratefloor_fix",
                     "metric_collector": "cbap_full_work_collector_v1"})
    meta = dict(manifest)
    meta.update({"status": "prepared", "exit_status": None,
                 "prepared_time_unix": time.time(), "log_truncated": False,
                 "scenario": row["scenario_id"],
                 "subcase": row["scenario_id"],
                 "algorithm": row["algorithm"], "algorithm_name": row["algorithm"],
                 "cc_mode": mode, "seed": int(row["seed"])})
    for name, value in (("manifest.json", manifest), ("run_meta.json", meta)):
        with open(os.path.join(run, name), "w") as stream:
            json.dump(value, stream, indent=2, sort_keys=True); stream.write("\n")
    with open(os.path.join(run, "command.txt"), "w") as stream:
        stream.write('python2 ./waf --cwd="%s" --run "scratch/third %s/config.txt"\n' %
                     (run, run))


if __name__ == "__main__": main()
