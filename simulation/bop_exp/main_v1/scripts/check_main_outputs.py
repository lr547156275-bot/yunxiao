#!/usr/bin/env python3
import argparse
import csv
import json
import math
import os
import sys
from mainlib import CASES, CONFIG, ROOT, SIM_ROOT, digest, registry, rows

REQUIRED = (
    "run_meta.json", "flow_summary.csv", "group_round_summary.csv",
    "queue_summary.csv", "congestion_summary.csv", "wire_summary.csv",
    "algorithm_summary.csv", "stdout.log", "exit_status.txt")
FORBIDDEN = {"bop_qc", "bop_qb_max", "bop_qb_prt",
             "bop_qb_oracle_q0"}
# These files select, launch, or validate runs but do not affect a prepared
# run's simulator inputs or control behavior. Bug fixes to them must not
# invalidate already-completed runs whose input and source hashes still match.
NON_RESULT_FRAMEWORK = {
    "config/run_manifest.csv",
    "scripts/check_main_outputs.py",
    "scripts/common.sh",
}


def csv_rows(path):
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def finite_csv(path):
    with open(path) as handle:
        text = handle.read().lower()
    return not any(token in text for token in (",nan", ",inf", ",-inf"))


def validate_run(run_dir, need_flag=True):
    errors = []
    for name in REQUIRED:
        if not os.path.isfile(os.path.join(run_dir, name)):
            errors.append("missing " + name)
    if need_flag and not os.path.isfile(os.path.join(run_dir,
                                                     "completed.flag")):
        errors.append("missing completed.flag")
    if errors:
        return errors
    with open(os.path.join(run_dir, "run_meta.json")) as handle:
        meta = json.load(handle)
    algorithm = meta["algorithm"]
    expected_run_id = "%s__%s__seed%d" % (
        meta["scenario"], algorithm, int(meta["seed"]))
    if meta.get("run_id") != expected_run_id:
        errors.append("run_id mismatch")
    reg = registry()
    if algorithm not in reg or algorithm in FORBIDDEN:
        errors.append("algorithm is unregistered or forbidden")
    elif int(reg[algorithm]["cc_mode"]) != int(meta["cc_mode"]):
        errors.append("CC_MODE registry mismatch")
    try:
        with open(os.path.join(run_dir, "exit_status.txt")) as handle:
            if int(handle.read().strip()) != 0:
                errors.append("nonzero exit status")
    except ValueError:
        errors.append("invalid exit status")
    for name, expected in meta.get("input_hashes", {}).items():
        path = os.path.join(run_dir, name)
        if not os.path.isfile(path) or digest(path) != expected:
            errors.append("input hash mismatch: " + name)
    for name, expected in meta.get("framework_hashes", {}).items():
        if name in NON_RESULT_FRAMEWORK:
            continue
        path = os.path.join(ROOT, name)
        if not os.path.isfile(path) or digest(path) != expected:
            errors.append("framework/input hash mismatch: " + name)
    for name, expected in meta.get("case_blueprint_hashes", {}).items():
        path = os.path.join(CASES, meta["scenario"], name)
        if not os.path.isfile(path) or digest(path) != expected:
            errors.append("case blueprint hash mismatch: " + name)
    if algorithm in reg:
        source = os.path.join(SIM_ROOT, reg[algorithm]["implementation_file"])
        if digest(source) != meta.get("algorithm_source_hash"):
            errors.append("algorithm source hash mismatch")
    for name in REQUIRED:
        if name.endswith(".csv") and os.path.exists(os.path.join(run_dir, name)):
            if not finite_csv(os.path.join(run_dir, name)):
                errors.append("NaN/Inf in " + name)
    flows = csv_rows(os.path.join(run_dir, "flow_summary.csv"))
    collective_n = int(meta["scenario_meta"]["senders"])
    if len(flows) != collective_n:
        errors.append("flow count mismatch")
    for row in flows:
        if row.get("completed") != "1":
            errors.append("incomplete flow " + row.get("flow_id", "?"))
        if int(float(row.get("acked_bytes", -1))) != int(
                float(row.get("total_size_bytes", -2))):
            errors.append("ACK byte mismatch " + row.get("flow_id", "?"))
    groups = csv_rows(os.path.join(run_dir, "group_round_summary.csv"))
    expected_rounds = int(meta["scenario_meta"]["rounds"])
    if len(groups) != expected_rounds:
        errors.append("group count mismatch")
    groups.sort(key=lambda x: int(x["round_id"]))
    for index, row in enumerate(groups):
        release = float(row["common_release_time"])
        finish = float(row["barrier_completion_time"])
        rct = float(row["group_rct"])
        if abs((finish - release) - rct) > 1e-9:
            errors.append("group RCT replay mismatch")
        if index and release < float(groups[index - 1][
                "barrier_completion_time"]) - 1e-12:
            errors.append("global barrier overlap")
    if meta.get("log_truncated"):
        errors.append("log truncated")
    with open(os.path.join(run_dir, "stdout.log"), errors="replace") as handle:
        if "LOG_TRUNCATED" in handle.read():
            errors.append("log truncated")
    round_path = os.path.join(run_dir, "round_summary.csv")
    if os.path.isfile(round_path):
        round_rows = csv_rows(round_path)
        if len(round_rows) != collective_n * expected_rounds:
            errors.append("flow-round count mismatch")
    if algorithm in ("bop", "bop_qb"):
        for name in ("bop_group_decisions.csv", "bop_flow_rates.csv"):
            if not os.path.isfile(os.path.join(run_dir, name)):
                errors.append("missing " + name)
        summary = csv_rows(os.path.join(run_dir, "algorithm_summary.csv"))[0]
        if float(summary["max_capacity_violation_bps"]) > 1:
            errors.append("BOP capacity violation")
        if algorithm == "bop_qb":
            raw_path = os.path.join(run_dir, "bop_group_decisions.csv")
            plan_path = os.path.join(run_dir, "bop_flow_rates.csv")
            if os.path.isfile(raw_path) and os.path.isfile(plan_path):
                decisions = csv_rows(raw_path)
                plans = csv_rows(plan_path)
                if len(decisions) != expected_rounds:
                    errors.append("BOP decision count mismatch")
                if len(plans) != collective_n * expected_rounds:
                    errors.append("BOP flow-plan count mismatch")
                for decision in decisions:
                    n = int(decision["participant_count"])
                    q0 = int(decision["residual_queue_bytes"])
                    target = int(decision["queue_target_bytes"])
                    margin = int(decision["packet_margin_bytes"])
                    total = int(decision["total_round_bytes"])
                    credit = int(decision["group_credit_bytes"])
                    if credit != min(max(target - q0 - margin, 0), total):
                        errors.append("BOP-QB formula replay mismatch")
                    selected = [x for x in plans
                                if x["group_id"] == decision["group_id"]
                                and x["round_id"] == decision["round_id"]]
                    if len(selected) != n or sum(int(x["qb_credit_bytes"])
                                                 for x in selected) != credit:
                        errors.append("BOP-QB flow credit mismatch")
                    if decision.get("safety_bound_valid") != "1":
                        errors.append("BOP-QB safety bound invalid")
    if algorithm == "pfc_only":
        path = os.path.join(run_dir, "controller_summary.csv")
        if os.path.isfile(path):
            for row in csv_rows(path):
                if int(float(row["direct_hpcc_updates"])) != 0 or \
                        float(row["rate_total_variation"]) != 0:
                    errors.append("pfc_only changed sender rate")
                    break
    return sorted(set(errors))


def check_matrix(root, seeds):
    manifest = rows(os.path.join(CONFIG, "run_manifest.csv"))
    wanted = [x for x in manifest if int(x["seed"]) in seeds]
    invalid = []
    hashes = {}
    round_hashes = {}
    for item in wanted:
        run_dir = os.path.join(root, item["scenario"], item["algorithm"],
                               "seed_%s" % item["seed"])
        errors = validate_run(run_dir)
        if errors:
            invalid.append({"run_id": item["run_id"],
                            "reason": "; ".join(errors)})
            continue
        with open(os.path.join(run_dir, "run_meta.json")) as handle:
            meta = json.load(handle)
        key = (item["scenario"], item["seed"])
        comparable = tuple(meta["input_hashes"][x] for x in (
            "topology.txt", "flow.txt", "rounds.txt", "fixed_paths.txt"))
        if key in hashes and hashes[key] != comparable:
            invalid.append({"run_id": item["run_id"],
                            "reason": "cross-algorithm input mismatch"})
        hashes[key] = comparable
        round_hashes.setdefault(item["scenario"], {})[
            int(item["seed"])] = meta["input_hashes"]["rounds.txt"]
    for scenario, values in round_hashes.items():
        if len(values) > 1 and len(set(values.values())) != len(values):
            invalid.append({"run_id": scenario,
                            "reason": "round hash unchanged across seeds"})
    fairness_scenarios = (
        "gap_20us_n16_64k", "msg_64k_n16_g50",
        "n32_64k_g50", "single_round_n16_64k")
    for scenario in fairness_scenarios:
        for seed in seeds:
            left = os.path.join(root, scenario, "dcqcn_wire_equalized",
                                "seed_%d" % seed, "wire_summary.csv")
            right = os.path.join(root, scenario, "bop_qb",
                                 "seed_%d" % seed, "wire_summary.csv")
            if not (os.path.isfile(left) and os.path.isfile(right)):
                continue
            equalized = csv_rows(left)[0]
            bop = csv_rows(right)[0]
            fields = ("application_payload_bytes", "data_packet_count",
                      "mean_wire_data_bytes", "min_wire_data_bytes",
                      "max_wire_data_bytes")
            if any(equalized[x] != bop[x] for x in fields):
                invalid.append({
                    "run_id": "%s__wire_fairness__seed%d" % (scenario, seed),
                    "reason": "equalized DCQCN/BOP-QB DATA wire mismatch"})
    out = os.path.join(root, "invalid_runs.csv")
    os.makedirs(root, exist_ok=True)
    with open(out, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["run_id", "reason"])
        writer.writeheader()
        writer.writerows(invalid)
    print("checked=%d invalid=%d" % (len(wanted), len(invalid)))
    return 0 if not invalid else 1


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("run")
    one.add_argument("run_dir")
    one.add_argument("--pre-complete", action="store_true")
    reuse = sub.add_parser("reuse")
    reuse.add_argument("run_dir")
    matrix = sub.add_parser("matrix")
    matrix.add_argument("root")
    matrix.add_argument("--seeds", default="1,2,3")
    args = parser.parse_args()
    if args.command in ("run", "reuse"):
        errors = validate_run(os.path.abspath(args.run_dir),
                              not getattr(args, "pre_complete", False))
        if errors:
            print("\n".join("FAIL " + x for x in errors))
            return 1
        print("PASS " + os.path.abspath(args.run_dir))
        return 0
    return check_matrix(os.path.abspath(args.root),
                        {int(x) for x in args.seeds.split(",") if x})


if __name__ == "__main__":
    sys.exit(main())
