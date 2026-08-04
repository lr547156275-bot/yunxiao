#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import time
from mainlib import CASES, CONFIG, SIM_ROOT, digest, registry, scenarios
from mainlib import write_round_inputs


OUTPUT_KEYS = {
    "PFC_OUTPUT_FILE": "pfc_events.csv",
    "FLOW_SUMMARY_FILE": "flow_summary.csv",
    "ROUND_SUMMARY_FILE": "round_summary.csv",
    "FEEDBACK_SUMMARY_FILE": "feedback_summary.csv",
    "CONTROLLER_SUMMARY_FILE": "controller_summary.csv",
    "GROUP_ROUND_SUMMARY_FILE": "group_round_summary.csv",
    "FLOW_PLAN_FILE": "flow_plan.csv",
    "LINK_TIMESERIES_FILE": "selected_link_timeseries.csv",
    "SELECTED_FLOW_TIMESERIES_FILE": "selected_flow_timeseries.csv",
    "WIRE_SIZE_SUMMARY_FILE": "raw_wire_size_summary.csv",
    "RELEASE_QUEUE_SUMMARY_FILE": "release_queue_summary.csv",
}


def git_commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=SIM_ROOT,
            text=True).strip()
    except Exception:
        return "UNKNOWN"


def rewrite_config(source, destination, updates):
    seen = set()
    output = []
    with open(source) as handle:
        for line in handle:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                key = stripped.split()[0]
                if key in updates:
                    output.append("%s %s\n" % (key, updates[key]))
                    seen.add(key)
                    continue
            output.append(line)
    for key, value in updates.items():
        if key not in seen:
            output.append("%s %s\n" % (key, value))
    with open(destination, "w") as handle:
        handle.writelines(output)


def prepare(args):
    algos = registry()
    specs = scenarios()
    if args.algorithm not in algos:
        raise SystemExit("unknown registered algorithm: " + args.algorithm)
    if args.scenario not in specs:
        raise SystemExit("unknown scenario: " + args.scenario)
    run_dir = os.path.abspath(args.run_dir)
    os.makedirs(run_dir, exist_ok=True)
    case_dir = os.path.join(CASES, args.scenario)
    for name in ("topology.txt", "trace.txt", "fixed_paths.txt",
                 "scenario_meta.json"):
        shutil.copy2(os.path.join(case_dir, name), os.path.join(run_dir, name))
    write_round_inputs(run_dir, specs[args.scenario], args.seed)
    reg = algos[args.algorithm]
    with open(os.path.join(run_dir, "scenario_meta.json")) as handle:
        scenario_meta = json.load(handle)
    bottleneck_node = int(scenario_meta["selected_bottleneck"].split(":")[0])
    updates = dict(OUTPUT_KEYS)
    updates.update({
        "TOPOLOGY_FILE": "topology.txt",
        "FLOW_FILE": "flow.txt",
        "FIXED_PATH_FILE": "fixed_paths.txt",
        "TRACE_FILE": "trace.txt",
        "ROUND_SCHEDULE_FILE": "rounds.txt",
        "CC_MODE": reg["cc_mode"],
        "SIM_SEED": str(args.seed),
        "SCENARIO": args.scenario,
        "ALGORITHM": args.algorithm,
        "CRFM_MIN_FREE_GB": str(args.min_free_gb),
        "FINAL_VALIDATION_ENABLE": "1",
        "FINAL_COLLECTIVE_FLOW_COUNT": specs[args.scenario]["senders"],
        "FINAL_PRIMER_FIRST_FLOW": "4294967295",
        "FINAL_BOTTLENECK_NODE": str(bottleneck_node),
        "FINAL_BOTTLENECK_IF": "1",
    })
    if args.algorithm == "bop_qb":
        updates["BOP_QB_GROUP_DECISIONS_FILE"] = \
            "bop_qb_group_decisions.csv"
    rewrite_config(os.path.join(case_dir, "config.txt"),
                   os.path.join(run_dir, "config.txt"), updates)
    hashes = {}
    for name in ("topology.txt", "flow.txt", "rounds.txt", "fixed_paths.txt",
                 "trace.txt", "config.txt"):
        hashes[name] = digest(os.path.join(run_dir, name))
    meta = {
        "run_id": "%s__%s__seed%d" % (
            args.scenario, args.algorithm, args.seed),
        "scenario": args.scenario,
        "algorithm": args.algorithm,
        "seed": args.seed,
        "cc_mode": int(reg["cc_mode"]),
        "algorithm_source_hash": reg["source_hash"],
        "algorithm_registry_hash": digest(os.path.join(
            CONFIG, "algorithm_registry.csv")),
        "input_hashes": hashes,
        "framework_hashes": {
            "config/main_scenarios.csv": digest(os.path.join(
                CONFIG, "main_scenarios.csv")),
            "config/algorithm_registry.csv": digest(os.path.join(
                CONFIG, "algorithm_registry.csv")),
            "config/run_manifest.csv": digest(os.path.join(
                CONFIG, "run_manifest.csv")),
            "config/metrics_schema.csv": digest(os.path.join(
                CONFIG, "metrics_schema.csv")),
            "scripts/mainlib.py": digest(os.path.join(
                os.path.dirname(__file__), "mainlib.py")),
            "scripts/generate_main_cases.py": digest(os.path.join(
                os.path.dirname(__file__), "generate_main_cases.py")),
            "scripts/collect_run_metrics.py": digest(os.path.join(
                os.path.dirname(__file__), "collect_run_metrics.py")),
            "scripts/check_main_outputs.py": digest(os.path.join(
                os.path.dirname(__file__), "check_main_outputs.py")),
            "scripts/prepare_main_run.py": digest(os.path.join(
                os.path.dirname(__file__), "prepare_main_run.py")),
            "scripts/common.sh": digest(os.path.join(
                os.path.dirname(__file__), "common.sh")),
        },
        "case_blueprint_hashes": {
            name: digest(os.path.join(case_dir, name))
            for name in ("topology.txt", "fixed_paths.txt", "trace.txt",
                         "scenario_meta.json", "config.txt")
        },
        "git_commit": git_commit(),
        "status": "prepared",
        "prepared_time_unix": time.time(),
        "log_truncated": False,
        "diagnostic_only": reg["diagnostic_only"] == "1",
        "baseline_only": reg["baseline_only"] == "1",
        "algorithm_name": args.algorithm,
        "algorithm_version": ("bop_qb_frozen_v1"
                              if args.algorithm == "bop_qb" else "native"),
        "queue_target_fraction": (0.5 if args.algorithm == "bop_qb" else None),
        "scenario_meta": scenario_meta,
    }
    with open(os.path.join(run_dir, "run_meta.json"), "w") as handle:
        json.dump(meta, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario")
    parser.add_argument("algorithm")
    parser.add_argument("seed", type=int)
    parser.add_argument("run_dir")
    parser.add_argument("--min-free-gb", type=float, default=5)
    prepare(parser.parse_args())


if __name__ == "__main__":
    main()
