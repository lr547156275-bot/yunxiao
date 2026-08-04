#!/usr/bin/env python3
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
ALGORITHMS = {
    "dcqcn": 1, "hpcc_int": 3, "bop_qb": 15,
    "independent_min_grant": 20, "cbap_init_only": 21,
    "cbap_rate_only": 22, "cbap_full": 23,
}
INPUTS = (
    "topology.txt", "flow.txt", "rounds.txt", "fixed_paths.txt",
    "controlled_links.txt", "controlled_paths.txt", "group_schedule.txt",
    "trace.txt", "scenario_meta.json", "input_hashes.json",
)


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rewrite(source, destination, updates):
    lines, seen = [], set()
    with open(source) as stream:
        for line in stream:
            stripped = line.strip()
            key = stripped.split()[0] if stripped else ""
            if key in updates:
                lines.append("%s %s\n" % (key, updates[key]))
                seen.add(key)
            else:
                lines.append(line)
    for key in sorted(set(updates) - seen):
        lines.append("%s %s\n" % (key, updates[key]))
    with open(destination, "w") as stream:
        stream.writelines(lines)


def manifest():
    path = os.path.join(ROOT, "config", "run_manifest.csv")
    with open(path, newline="") as stream:
        return {row["run_id"]: row for row in csv.DictReader(stream)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    parser.add_argument("run_dir")
    parser.add_argument("--min-free-gb", type=float, default=5)
    args = parser.parse_args()
    rows = manifest()
    if args.run_id not in rows:
        raise SystemExit("unknown run_id")
    row = rows[args.run_id]
    algorithm = row["algorithm"]
    if algorithm not in ALGORITHMS:
        raise SystemExit("unknown algorithm")
    case = os.path.join(ROOT, "cases", row["scenario"], row["subcase"])
    run_dir = os.path.abspath(args.run_dir)
    os.makedirs(run_dir, exist_ok=True)
    for name in INPUTS:
        shutil.copy2(os.path.join(case, name),
                     os.path.join(run_dir, name))
    cbap = algorithm in (
        "independent_min_grant", "cbap_init_only",
        "cbap_rate_only", "cbap_full")
    updates = {
        "CC_MODE": ALGORITHMS[algorithm],
        "SIM_SEED": row["seed"],
        "ALGORITHM": algorithm,
        "SCENARIO": row["scenario"] + "__" + row["subcase"],
        "PFC_RUNTIME_ENABLE":
            int(json.load(open(os.path.join(case, "scenario_meta.json")))
                ["pfc_runtime_enabled"]),
        "CRFM_MIN_FREE_GB": args.min_free_gb,
        "CBAP_ENABLE": int(cbap),
        "CBAP_PORT_SUMMARY_FILE": "cbap_port_summary.csv",
        "CBAP_ADMISSION_FILE": "cbap_admission.csv",
        "CBAP_RATE_TRANSITION_FILE": "cbap_rate_transitions.csv",
        "CBAP_FLOW_STATE_FILE": "cbap_flow_state.csv",
        "CBAP_CONTROL_OVERHEAD_FILE": "cbap_control_overhead.csv",
        "CBAP_PACKET_TRACE_FILE": "cbap_packet_trace.csv",
        "CBAP_PACKET_TRACE_MAX_MB": 128,
    }
    rewrite(os.path.join(case, "config.txt"),
            os.path.join(run_dir, "config.txt"), updates)
    hashes = dict((name, digest(os.path.join(run_dir, name)))
                  for name in INPUTS if name != "input_hashes.json")
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO,
        text=True).strip()
    meta = {
        "run_id": args.run_id,
        "scenario": row["scenario"],
        "subcase": row["subcase"],
        "algorithm": algorithm,
        "algorithm_name": algorithm,
        "algorithm_version": "cbap_v0" if cbap else "frozen_existing",
        "diagnostic_only": algorithm == "independent_min_grant",
        "cc_mode": ALGORITHMS[algorithm],
        "seed": int(row["seed"]),
        "formal": True,
        "git_commit": commit,
        "input_hashes": hashes,
        "control_epoch_us": 5 if cbap else None,
        "planning_delay_us": 5 if cbap else 0,
        "control_delay_us": 5 if cbap else 0,
        "cbap_data_header_bytes": 0 if cbap else None,
        "packet_trace_enabled": int(row["seed"]) == 1,
        "packet_trace_scope": "controlled_egress_data_dequeue"
            if int(row["seed"]) == 1 else "disabled",
        "prepared_time_unix": time.time(),
        "status": "prepared",
        "exit_status": None,
        "log_truncated": False,
    }
    with open(os.path.join(run_dir, "run_meta.json"), "w") as stream:
        json.dump(meta, stream, indent=2, sort_keys=True)
        stream.write("\n")
    with open(os.path.join(run_dir, "manifest.json"), "w") as stream:
        json.dump({"run_id": args.run_id, "scenario": row["scenario"],
                   "subcase": row["subcase"], "algorithm": algorithm,
                   "cc_mode": ALGORITHMS[algorithm],
                   "seed": int(row["seed"]),
                   "input_hashes": hashes},
                  stream, indent=2, sort_keys=True)
        stream.write("\n")
    with open(os.path.join(run_dir, "command.txt"), "w") as stream:
        stream.write('python2 ./waf --cwd="%s" --run '
                     '"scratch/third %s/config.txt"\n' %
                     (run_dir, run_dir))
    with open(os.path.join(run_dir, "git_commit.txt"), "w") as stream:
        stream.write(commit + "\n")


if __name__ == "__main__":
    main()
