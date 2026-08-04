#!/usr/bin/env python3
import argparse, csv, hashlib, json, math, os, shutil, subprocess, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(ROOT, ".."))


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rewrite(src, dst, updates):
    lines, seen = [], set()
    for line in open(src):
        words = line.split(); key = words[0] if words else ""
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
    p.add_argument("manifest"); p.add_argument("run_id"); p.add_argument("run_dir")
    p.add_argument("--min-free-gb", type=float, default=5)
    a = p.parse_args()
    table = {x["run_id"]: x for x in csv.DictReader(open(a.manifest))}
    if a.run_id not in table:
        raise SystemExit("unknown run_id")
    row = table[a.run_id]; case = os.path.join(ROOT, "cases", row["scenario"])
    run = os.path.abspath(a.run_dir); os.makedirs(run, exist_ok=True)
    for name in os.listdir(case):
        src = os.path.join(case, name)
        if os.path.isfile(src) and name != "config.txt":
            shutil.copy2(src, os.path.join(run, name))
    mode = int(row["cc_mode"]); cbap = mode in (24, 25); scoped = cbap
    policy = int(row["rate_floor_policy"])
    updates = {
        "CC_MODE": mode, "SIM_SEED": row["seed"],
        "ALGORITHM": row["algorithm_name"], "SCENARIO": row["scenario"],
        "CBAP_ENABLE": int(cbap), "CBAP_VERSION": row["cbap_version"],
        "CBAP_INCREASE_POLICY": 1 if cbap else 0,
        "CBAP_INCREASE_FRACTION": "0.10",
        "CBAP_INCREASE_ABSOLUTE_BPS": 2000000000,
        "CBAP_SCOPE_POLICY": 1 if scoped else 0, "CBAP_SCOPE_BASE_CC": 1,
        "CBAP_RATE_FLOOR_POLICY": policy,
        "CBAP_RATEFLOOR_SEMANTIC_ZERO_TEST": row["semantic_zero_test"],
        "CBAP_RATEFLOOR_SEMANTIC_ZERO_FLOW": row["semantic_zero_flow"],
        "CBAP_RATEFLOOR_SEMANTIC_ZERO_START_EPOCH": row["semantic_zero_start_epoch"],
        "CBAP_RATEFLOOR_SEMANTIC_ZERO_END_EPOCH": row["semantic_zero_end_epoch"],
        "CBAP_APPLIED_RATE_AUDIT_FILE": "applied_rate_audit.csv" if cbap else "/dev/null",
        "CBAP_SCOPE_SUMMARY_FILE": "scope_summary.csv" if cbap else "/dev/null",
        "CBAP_SCOPE_LINK_FILE": "scope_link_summary.csv" if cbap else "/dev/null",
        "CBAP_PACKET_TRACE_FILE": "cbap_packet_trace.csv" if cbap else "/dev/null",
        "CBAP_PACKET_TRACE_MAX_MB": 256,
        "CBAP_TX_EVENT_FILE": "sender_tx_trace.csv" if cbap else "/dev/null",
        "CBAP_INCREASE_AUDIT_FILE": "increase_policy_events.csv" if cbap else "/dev/null",
        "CRFM_MIN_FREE_GB": a.min_free_gb,
    }
    rewrite(os.path.join(case, "config.txt"), os.path.join(run, "config.txt"), updates)
    input_names = ("topology.txt", "flow.txt", "trace.txt", "rounds.txt",
                   "fixed_paths.txt", "controlled_links.txt",
                   "controlled_paths.txt", "group_schedule.txt",
                   "scenario_meta.json", "v13_input_hashes.json")
    hashes = {n: sha(os.path.join(run, n)) for n in input_names
              if os.path.isfile(os.path.join(run, n))}
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"],
                                     cwd=REPO, text=True).strip()
    legacy_floor = int(math.ceil(8 * 1064 * 1e9 / 5000.0))
    manifest = dict(row)
    manifest.update({
        "algorithm_name": row["algorithm_name"],
        "algorithm": row["algorithm_name"],
        "scope_decision": "PENDING" if scoped else "NOT_APPLICABLE",
        "scope_policy": row["scope_policy"],
        "rate_floor_policy": "EXACT_GRANT_PACING" if policy else
                             "ONE_PACKET_PER_EPOCH_LEGACY",
        "control_epoch_ns": 5000, "max_wire_packet_bytes": 1064,
        "legacy_floor_rate_bps": legacy_floor,
        "git_commit": commit, "input_hashes": hashes,
    })
    meta = dict(manifest)
    meta.update({"status": "prepared", "exit_status": None,
                 "prepared_time_unix": time.time(), "log_truncated": False})
    for name, obj in (("manifest.json", manifest), ("run_meta.json", meta)):
        with open(os.path.join(run, name), "w") as f:
            json.dump(obj, f, indent=2, sort_keys=True); f.write("\n")
    with open(os.path.join(run, "command.txt"), "w") as f:
        f.write('python2 ./waf --cwd="%s" --run "scratch/third %s/config.txt"\n' %
                (run, run))


if __name__ == "__main__":
    main()
