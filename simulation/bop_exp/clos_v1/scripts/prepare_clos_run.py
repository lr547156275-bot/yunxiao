#!/usr/bin/env python3
import argparse
import csv
import json
import os
import shutil
import subprocess
import time

from closlib import ALGORITHMS, CASES, CONFIG, ROOT, digest, input_hashes

OUTPUTS = {
    "PFC_OUTPUT_FILE": "pfc_events.csv",
    "FLOW_SUMMARY_FILE": "flow_summary.csv",
    "ROUND_SUMMARY_FILE": "round_summary.csv",
    "FEEDBACK_SUMMARY_FILE": "feedback_summary.csv",
    "CONTROLLER_SUMMARY_FILE": "controller_summary.csv",
    "GROUP_ROUND_SUMMARY_FILE": "group_round_summary.csv",
    "FLOW_PLAN_FILE": "flow_plan.csv",
    "LINK_TIMESERIES_FILE": "selected_link_timeseries.csv",
    "SELECTED_FLOW_TIMESERIES_FILE": "selected_flow_timeseries.csv",
}


def manifest():
    with open(os.path.join(CONFIG, "run_manifest.csv"), newline="") as handle:
        return {row["run_id"]: row for row in csv.DictReader(handle)}


def rewrite_config(source, destination, updates):
    seen, lines = set(), []
    with open(source) as handle:
        for line in handle:
            stripped = line.strip()
            key = stripped.split()[0] if stripped and not \
                stripped.startswith("#") else None
            if key in updates:
                lines.append("%s %s\n" % (key, updates[key]))
                seen.add(key)
            else:
                lines.append(line)
    for key, value in updates.items():
        if key not in seen:
            lines.append("%s %s\n" % (key, value))
    with open(destination, "w") as handle:
        handle.writelines(lines)


def git_commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=os.path.join(ROOT, "..", ".."),
            text=True).strip()
    except Exception:
        return "UNKNOWN"


def prepare(args):
    rows = manifest()
    if args.run_id not in rows:
        raise SystemExit("unknown run_id: " + args.run_id)
    row = rows[args.run_id]
    algorithm, seed = row["algorithm"], int(row["seed"])
    if algorithm not in ALGORITHMS:
        raise SystemExit("unregistered formal algorithm")
    case_dir = os.path.join(CASES, row["scenario"], "seed_%d" % seed)
    run_dir = os.path.abspath(args.run_dir)
    os.makedirs(run_dir, exist_ok=True)
    names = ("topology.txt", "flow.txt", "rounds.txt", "fixed_paths.txt",
             "multilink_links.txt", "multilink_paths.txt",
             "group_schedule.txt", "collective_schedule.csv", "trace.txt",
             "scenario_meta.json", "input_hashes.json")
    for name in names:
        shutil.copy2(os.path.join(case_dir, name),
                     os.path.join(run_dir, name))
    updates = dict(OUTPUTS)
    updates.update({
        "CC_MODE": ALGORITHMS[algorithm], "SIM_SEED": seed,
        "SCENARIO": row["scenario"], "ALGORITHM": algorithm,
        "CRFM_MIN_FREE_GB": args.min_free_gb,
        "FIXED_PATH_OUTPUT_FILE": "resolved_fixed_paths.csv",
        "FINAL_VALIDATION_ENABLE": 0,
    })
    if algorithm == "bop_qb":
        updates.update({
            "BOP_QB_GROUP_DECISIONS_FILE":
                "bop_qb_group_decisions.csv",
            "BOP_MULTILINK_GROUP_DECISIONS_FILE":
                "bop_multilink_group_decisions.csv",
            "BOP_MULTILINK_LINK_CONSTRAINTS_FILE":
                "bop_multilink_link_constraints.csv",
        })
    rewrite_config(os.path.join(case_dir, "config.txt"),
                   os.path.join(run_dir, "config.txt"), updates)
    hashes = input_hashes(run_dir)
    expected = json.load(open(os.path.join(case_dir, "input_hashes.json")))
    if hashes != expected:
        raise SystemExit("copied input hash differs from case blueprint")
    meta = {
        "run_id": args.run_id, "scenario": row["scenario"],
        "topology": row["topology"], "collective": row["collective"],
        "participants": int(row["participants"]), "message": row["message"],
        "section": row["section"], "algorithm": algorithm,
        "algorithm_name": algorithm,
        "algorithm_version": ("bop_qb_frozen_multilink_v1"
                              if algorithm == "bop_qb" else "native_frozen"),
        "cc_mode": ALGORITHMS[algorithm], "seed": seed,
        "input_hashes": hashes, "git_commit": git_commit(),
        "prepared_time_unix": time.time(), "status": "prepared",
        "log_truncated": False, "bop_multilink_enable": True,
        "background_bps": 0,
        "queue_target_fraction": 0.5 if algorithm == "bop_qb" else None,
        "pfc_metric_semantics": "NA_event_chain_not_validated",
        "dropped_packets": "NA", "retransmitted_packets": "NA",
        "synthetic_dlrm_like": row["collective"] == "dlrm_like",
    }
    with open(os.path.join(run_dir, "run_meta.json"), "w") as handle:
        json.dump(meta, handle, indent=2, sort_keys=True)
        handle.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    parser.add_argument("run_dir")
    parser.add_argument("--min-free-gb", type=float, default=5)
    prepare(parser.parse_args())

