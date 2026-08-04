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


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rewrite(source, destination, updates):
    lines, seen = [], set()
    for line in open(source):
        words = line.split()
        key = words[0] if words else ""
        if key in updates:
            lines.append("%s %s\n" % (key, updates[key]))
            seen.add(key)
        else:
            lines.append(line)
    for key in sorted(set(updates) - seen):
        lines.append("%s %s\n" % (key, updates[key]))
    with open(destination, "w") as stream:
        stream.writelines(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("run_id")
    parser.add_argument("run_dir")
    parser.add_argument("--min-free-gb", type=float, default=5)
    args = parser.parse_args()
    rows = {row["run_id"]: row for row in csv.DictReader(open(args.manifest))}
    if args.run_id not in rows:
        raise SystemExit("unknown run_id: %s" % args.run_id)
    row = rows[args.run_id]
    case = os.path.join(ROOT, "cases", row["scenario"])
    run = os.path.abspath(args.run_dir)
    os.makedirs(run, exist_ok=True)
    for entry in os.listdir(case):
        source = os.path.join(case, entry)
        if os.path.isfile(source) and entry != "config.txt":
            shutil.copy2(source, os.path.join(run, entry))

    mode = int(row["cc_mode"])
    if mode not in (28, 29):
        raise SystemExit("v2.0 manifest has unexpected CC_MODE")
    fraction = float(row["queue_target_fraction"])
    updates = {
        "CC_MODE": mode,
        "SIM_SEED": int(row["seed"]),
        "ALGORITHM": row["algorithm_name"],
        "SCENARIO": row["scenario"],
        "CBAP_ENABLE": 1,
        "CBAP_VERSION": "v2.0",
        "CBAP_QUEUE_TARGET_FRACTION": format(fraction, ".6g"),
        "CBAP_SCOPE_POLICY": 0,
        "CBAP_SCOPE_BASE_CC": 1,
        "CBAP_RATE_FLOOR_POLICY": 1,
        "CBAP_INCREASE_POLICY": 1,
        "CBAP_INCREASE_FRACTION": "0.10",
        "CBAP_INCREASE_ABSOLUTE_BPS": 2000000000,
        "CBAP_HANDOFF_ENABLE": 0,
        "CBAP_HANDOFF_STABLE_EPOCHS": 2,
        "CBAP_HANDOFF_BASE_CC": 1,
        "CBAP_V20_BATCH_FILE": "cbap_v20_batch.csv",
        "CBAP_V20_FLOW_FILE": "cbap_v20_flow.csv",
        "CBAP_PORT_SUMMARY_FILE": "cbap_port_summary.csv",
        "CBAP_ADMISSION_FILE": "cbap_admission.csv",
        "CBAP_RATE_TRANSITION_FILE": "cbap_rate_transitions.csv",
        "CBAP_FLOW_STATE_FILE": "cbap_flow_state.csv",
        "CBAP_APPLIED_RATE_AUDIT_FILE": "applied_rate_audit.csv",
        "CBAP_CONTROLLER_OWNERSHIP_FILE": "controller_ownership.csv",
        "CBAP_CONTROL_MESSAGE_FILE": "control_message_audit.csv",
        "CBAP_PACKET_TRACE_FILE": "/dev/null",
        "CBAP_PACKET_TRACE_MAX_MB": 96,
        "CBAP_TX_EVENT_FILE": "sender_tx_trace.csv",
        "CBAP_TX_TRACE_TRACKING_PACKETS": 4096,
        "CBAP_INCREASE_AUDIT_FILE": "/dev/null",
        "CBAP_HANDOFF_SUMMARY_FILE": "/dev/null",
        "CBAP_HANDOFF_FLOW_FILE": "/dev/null",
        "CBAP_ENVELOPE_LINK_FILE": "/dev/null",
        "CBAP_ENVELOPE_FLOW_FILE": "/dev/null",
        "CBAP_INCUMBENT_PROGRESS_FILE": "incumbent_summary.csv",
        "CRFM_MIN_FREE_GB": args.min_free_gb,
    }
    rewrite(os.path.join(case, "config.txt"),
            os.path.join(run, "config.txt"), updates)

    input_names = ("topology.txt", "flow.txt", "trace.txt", "rounds.txt",
                   "fixed_paths.txt", "controlled_links.txt",
                   "controlled_paths.txt", "group_schedule.txt",
                   "scenario_meta.json")
    hashes = {name: sha256(os.path.join(run, name)) for name in input_names}
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"],
                                     cwd=REPO, text=True).strip()
    meta = dict(row)
    meta.update({
        "algorithm": row["algorithm_name"],
        "algorithm_version": "cbap_v20_startup_handoff",
        "cc_mode": mode,
        "base_cc": "DCQCN" if mode == 28 else "HPCC_INT",
        "queue_target_fraction": fraction,
        "classification_inputs":
            "fixed_path,remaining_bytes,max_rate,rtt,fresh_port_summary",
        "startup_lease": "min(fresh_feedback,2*rtt,pfc,q_high,path_stale)",
        "post_handoff_owner": "BASE_CC_ONLY",
        "tracking_after_handoff": False,
        "git_commit": commit,
        "input_hashes": hashes,
        "status": "prepared",
        "exit_status": None,
        "prepared_time_unix": time.time(),
        "ns3_executed": False,
        "log_truncated": False,
    })
    for name in ("manifest.json", "run_meta.json"):
        with open(os.path.join(run, name), "w") as stream:
            json.dump(meta, stream, indent=2, sort_keys=True)
            stream.write("\n")
    with open(os.path.join(run, "command.txt"), "w") as stream:
        stream.write('python2 ./waf --cwd="%s" --run '
                     '"scratch/third %s/config.txt"\n' % (run, run))


if __name__ == "__main__":
    main()
