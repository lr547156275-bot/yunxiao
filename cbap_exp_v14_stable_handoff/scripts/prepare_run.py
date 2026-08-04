#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(ROOT, ".."))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rewrite(src, dst, updates):
    lines, seen = [], set()
    for line in open(src):
        words = line.split()
        key = words[0] if words else ""
        if key in updates:
            lines.append("%s %s\n" % (key, updates[key])); seen.add(key)
        else:
            lines.append(line)
    for key in sorted(set(updates) - seen):
        lines.append("%s %s\n" % (key, updates[key]))
    with open(dst, "w") as f:
        f.writelines(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("manifest")
    p.add_argument("run_id")
    p.add_argument("run_dir")
    p.add_argument("--min-free-gb", type=float, default=5)
    args = p.parse_args()
    rows = {r["run_id"]: r for r in csv.DictReader(open(args.manifest))}
    if args.run_id not in rows:
        raise SystemExit("unknown run_id: %s" % args.run_id)
    row = rows[args.run_id]
    case = os.path.join(ROOT, "cases", row["scenario"])
    run = os.path.abspath(args.run_dir)
    os.makedirs(run, exist_ok=True)
    for name in os.listdir(case):
        src = os.path.join(case, name)
        if os.path.isfile(src) and name != "config.txt":
            shutil.copy2(src, os.path.join(run, name))

    mode = int(row["cc_mode"])
    cbap = mode in (21, 25, 26)
    scoped = mode in (25, 26)
    handoff = mode == 26
    updates = {
        "CC_MODE": mode,
        "SIM_SEED": row["seed"],
        "ALGORITHM": row["algorithm_name"],
        "SCENARIO": row["scenario"],
        "CBAP_ENABLE": int(cbap),
        "CBAP_VERSION": row["cbap_version"],
        "CBAP_INCREASE_POLICY": 1 if mode in (25, 26) else 0,
        "CBAP_INCREASE_FRACTION": "0.10",
        "CBAP_INCREASE_ABSOLUTE_BPS": 2000000000,
        "CBAP_SCOPE_POLICY": 1 if scoped else 0,
        "CBAP_SCOPE_BASE_CC": 1,
        "CBAP_RATE_FLOOR_POLICY": row["rate_floor_policy"],
        "CBAP_RATEFLOOR_SEMANTIC_ZERO_TEST": 0,
        "CBAP_HANDOFF_ENABLE": int(handoff),
        "CBAP_HANDOFF_STABLE_EPOCHS": 2,
        "CBAP_HANDOFF_BASE_CC": 1,
        "CBAP_HANDOFF_DIAGNOSTIC_FORCE_ROOT":
            row.get("diagnostic_force_root", "0"),
        "CBAP_HANDOFF_DIAGNOSTIC_RECOVERY_UNTIL_EPOCH":
            row.get("diagnostic_recovery_until_epoch", "0"),
        "CBAP_APPLIED_RATE_AUDIT_FILE":
            "applied_rate_audit.csv" if cbap else "/dev/null",
        "CBAP_SCOPE_SUMMARY_FILE":
            "scope_summary.csv" if cbap else "/dev/null",
        "CBAP_SCOPE_LINK_FILE":
            "scope_link_summary.csv" if cbap else "/dev/null",
        # The legacy all-DATA packet trace duplicates sender_tx_trace and
        # necessarily truncates in the 4 MiB semantic case. Handoff packet
        # correctness uses the bounded sender trace plus handoff_flow records.
        "CBAP_PACKET_TRACE_FILE": "/dev/null",
        "CBAP_PACKET_TRACE_MAX_MB": 96,
        "CBAP_TX_EVENT_FILE":
            "sender_tx_trace.csv" if cbap else "/dev/null",
        "CBAP_INCREASE_AUDIT_FILE":
            "increase_policy_events.csv" if cbap else "/dev/null",
        "CBAP_HANDOFF_SUMMARY_FILE":
            "cbap_handoff_summary.csv" if mode in (25, 26) else "/dev/null",
        "CBAP_HANDOFF_FLOW_FILE":
            "cbap_handoff_flow.csv" if mode in (25, 26) else "/dev/null",
        "CBAP_CONTROLLER_OWNERSHIP_FILE":
            "controller_ownership.csv" if handoff else "/dev/null",
        "CBAP_CONTROL_MESSAGE_FILE":
            "control_message_audit.csv" if mode in (25, 26) else "/dev/null",
        "CRFM_MIN_FREE_GB": args.min_free_gb,
    }
    rewrite(os.path.join(case, "config.txt"),
            os.path.join(run, "config.txt"), updates)

    input_names = ("topology.txt", "flow.txt", "trace.txt", "rounds.txt",
                   "fixed_paths.txt", "controlled_links.txt",
                   "controlled_paths.txt", "group_schedule.txt",
                   "scenario_meta.json", "v14_input_hashes.json")
    hashes = {name: sha256(os.path.join(run, name)) for name in input_names
              if os.path.isfile(os.path.join(run, name))}
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"],
                                     cwd=REPO, text=True).strip()
    minimum_tracking = "max(2*measured_path_rtt_ns,2*control_epoch_ns)"
    manifest = dict(row)
    manifest.update({
        "algorithm": row["algorithm_name"],
        "algorithm_name": row["algorithm_name"],
        "cbap_version": row["cbap_version"],
        "cc_mode": mode,
        "scope_policy": row["scope_policy"],
        "rate_floor_policy": "EXACT_GRANT_PACING" if
            int(row["rate_floor_policy"]) else "ONE_PACKET_PER_EPOCH_LEGACY",
        "handoff_policy": "STABLE_BATCH_ONCE" if handoff else
            ("SHADOW_ONLY" if mode == 25 else "NONE"),
        "base_cc": "DCQCN" if handoff else "N/A",
        "control_epoch_ns": 5000,
        "stable_epochs_required": 2,
        "minimum_tracking_time_ns": minimum_tracking,
        "git_commit": commit,
        "input_hashes": hashes,
        "legacy_floor_rate_bps": int(math.ceil(8 * 1064 * 1e9 / 5000.0)),
    })
    meta = dict(manifest)
    meta.update(status="prepared", exit_status=None,
                prepared_time_unix=time.time(), log_truncated=False,
                ns3_executed=False)
    for name, obj in (("manifest.json", manifest), ("run_meta.json", meta)):
        with open(os.path.join(run, name), "w") as f:
            json.dump(obj, f, indent=2, sort_keys=True); f.write("\n")
    with open(os.path.join(run, "command.txt"), "w") as f:
        f.write('python2 ./waf --cwd="%s" --run "scratch/third %s/config.txt"\n'
                % (run, run))


if __name__ == "__main__":
    main()
