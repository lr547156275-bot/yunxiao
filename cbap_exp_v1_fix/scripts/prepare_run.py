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
MODES = {
    "dcqcn": 1, "hpcc_int": 3, "bop_qb": 15,
    "independent_min_grant": 20, "cbap_init_only": 21,
    "cbap_rate_only": 22, "cbap_full": 23,
}
INPUTS = (
    "topology.txt", "flow.txt", "rounds.txt", "fixed_paths.txt",
    "controlled_links.txt", "controlled_paths.txt", "group_schedule.txt",
    "trace.txt", "scenario_meta.json", "input_hashes.json",
    "input_hashes_v1.json",
)


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rewrite(source, destination, updates):
    output, seen = [], set()
    for line in open(source):
        key = line.strip().split()[0] if line.strip() else ""
        if key in updates:
            output.append("%s %s\n" % (key, updates[key]))
            seen.add(key)
        else:
            output.append(line)
    for key in sorted(set(updates) - seen):
        output.append("%s %s\n" % (key, updates[key]))
    with open(destination, "w") as stream:
        stream.writelines(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("run_id")
    parser.add_argument("run_dir")
    parser.add_argument("--min-free-gb", type=float, default=5)
    args = parser.parse_args()
    rows = {r["run_id"]: r for r in csv.DictReader(open(args.manifest))}
    if args.run_id not in rows:
        raise SystemExit("unknown run_id")
    row = rows[args.run_id]
    algorithm = row["algorithm"]
    if algorithm not in MODES or int(row["cc_mode"]) != MODES[algorithm]:
        raise SystemExit("algorithm/CC_MODE mismatch")
    case = os.path.join(ROOT, "cases", row["scenario"], row["subcase"])
    run = os.path.abspath(args.run_dir)
    os.makedirs(run, exist_ok=True)
    for name in INPUTS:
        source = os.path.join(case, name)
        if os.path.isfile(source):
            shutil.copy2(source, os.path.join(run, name))
    cbap = algorithm in (
        "independent_min_grant", "cbap_init_only",
        "cbap_rate_only", "cbap_full")
    scenario_meta = json.load(open(os.path.join(case, "scenario_meta.json")))
    updates = {
        "CC_MODE": MODES[algorithm], "SIM_SEED": row["seed"],
        "ALGORITHM": algorithm,
        "SCENARIO": row["scenario"] + "__" + row["subcase"],
        "PFC_RUNTIME_ENABLE": int(scenario_meta["pfc_runtime_enabled"]),
        "CRFM_MIN_FREE_GB": args.min_free_gb,
        "CBAP_ENABLE": int(cbap),
        "CBAP_PORT_SUMMARY_FILE": "cbap_port_summary.csv",
        "CBAP_ADMISSION_FILE": "cbap_admission.csv",
        "CBAP_RATE_TRANSITION_FILE": "cbap_rate_transitions.csv",
        "CBAP_FLOW_STATE_FILE": "cbap_flow_state.csv",
        "CBAP_CONTROL_OVERHEAD_FILE": "cbap_control_overhead.csv",
        "CBAP_TX_EVENT_FILE": "cbap_tx_events.csv" if cbap else "/dev/null",
        "CBAP_TX_TRACE_TRACKING_PACKETS": 4096,
        "CBAP_PACKET_TRACE_FILE": "cbap_packet_trace.csv",
        "CBAP_PACKET_TRACE_MAX_MB": 128,
    }
    rewrite(os.path.join(case, "config.txt"), os.path.join(run, "config.txt"),
            updates)
    hashes = {name: digest(os.path.join(run, name)) for name in INPUTS
              if os.path.isfile(os.path.join(run, name)) and
              not name.startswith("input_hashes")}
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    meta = {
        "run_id": args.run_id, "scenario": row["scenario"],
        "subcase": row["subcase"], "algorithm": algorithm,
        "algorithm_name": algorithm,
        "algorithm_version": "cbap_v1_admission_credit_fix"
            if cbap else "frozen_existing",
        "diagnostic_only": algorithm == "independent_min_grant",
        "cc_mode": MODES[algorithm], "seed": int(row["seed"]),
        "formal": bool(int(row["formal"])), "git_commit": commit,
        "input_hashes": hashes, "control_epoch_us": 5 if cbap else None,
        "planning_delay_us": 5 if cbap else 0,
        "control_delay_us": 5 if cbap else 0,
        "credit_scope": "admission_hold_only" if algorithm == "cbap_full"
            else "disabled",
        "tx_event_source": "sender_qbb_transmit_start_callback"
            if cbap else "disabled",
        "prepared_time_unix": time.time(), "status": "prepared",
        "exit_status": None, "log_truncated": False,
    }
    for name, data in (("run_meta.json", meta),
                       ("manifest.json", dict(row, input_hashes=hashes))):
        with open(os.path.join(run, name), "w") as stream:
            json.dump(data, stream, indent=2, sort_keys=True)
            stream.write("\n")
    with open(os.path.join(run, "command.txt"), "w") as stream:
        stream.write('python2 ./waf --cwd="%s" --run '
                     '"scratch/third %s/config.txt"\n' % (run, run))
    with open(os.path.join(run, "git_commit.txt"), "w") as stream:
        stream.write(commit + "\n")


if __name__ == "__main__":
    main()
