#!/usr/bin/env python3
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT.parents[1]
V1 = ROOT.parent / "main_v1"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rewrite(path, updates):
    lines, seen = [], set()
    for line in path.read_text().splitlines(True):
        stripped = line.strip()
        key = stripped.split()[0] if stripped and not stripped.startswith("#") else ""
        if key in updates:
            lines.append("%s %s\n" % (key, updates[key]))
            seen.add(key)
        else:
            lines.append(line)
    for key, value in updates.items():
        if key not in seen:
            lines.append("%s %s\n" % (key, value))
    path.write_text("".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario")
    parser.add_argument("algorithm")
    parser.add_argument("run_dir")
    parser.add_argument("--min-free-gb", default="5")
    args = parser.parse_args()
    source = {
        "open_loop_pfc_configured": "pfc_only",
        "open_loop_pfc_disabled": "pfc_only",
    }.get(args.algorithm, args.algorithm)
    run_dir = Path(args.run_dir).resolve()
    subprocess.check_call([
        sys.executable, str(V1 / "scripts/prepare_main_run.py"),
        args.scenario, source, "1", str(run_dir),
        "--min-free-gb", str(args.min_free_gb)])
    scenario_meta = json.load(open(run_dir / "scenario_meta.json"))
    node, interface = scenario_meta["selected_bottleneck"].split(":")
    updates = {
        "ALGORITHM": args.algorithm,
        "PFC_RUNTIME_ENABLE":
            "0" if args.algorithm == "open_loop_pfc_disabled" else "1",
        "PFC_SEMANTIC_AUDIT_ENABLE": "1",
        "PFC_AUDIT_NODE": node, "PFC_AUDIT_IF": interface,
        "PFC_AUDIT_PRIORITY": "3",
        "PFC_EVENT_TRACE_FILE": "pfc_event_trace.csv",
        "PFC_SEMANTIC_SUMMARY_FILE": "pfc_semantic_summary.json",
    }
    rewrite(run_dir / "config.txt", updates)
    meta_path = run_dir / "run_meta.json"
    meta = json.load(open(meta_path))
    meta.update({
        "run_id": "%s__%s__seed1" % (args.scenario, args.algorithm),
        "algorithm": args.algorithm, "algorithm_name": args.algorithm,
        "baseline_class": ("open_loop_reference" if
                           args.algorithm == "open_loop_pfc_configured"
                           else "diagnostic_open_loop" if
                           args.algorithm == "open_loop_pfc_disabled"
                           else "formal_or_proposed_audit"),
        "diagnostic_only": True,
        "pfc_runtime_enabled":
            args.algorithm != "open_loop_pfc_disabled",
        "pfc_semantic_audit": True,
    })
    meta["input_hashes"]["config.txt"] = digest(run_dir / "config.txt")
    with open(meta_path, "w") as stream:
        json.dump(meta, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main()
