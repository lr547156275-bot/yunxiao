#!/usr/bin/env python3
"""Static/input and output validator for exact n32 DCQCN replay."""
import argparse
import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT.parents[1]
MANIFEST = ROOT / "config/dcqcn_n32_replay_manifest.csv"
INPUT_MAP = {
    "topology.txt": "topology_sha256",
    "flow.txt": "flow_sha256",
    "rounds.txt": "rounds_sha256",
    "fixed_paths.txt": "fixed_paths_sha256",
    "trace.txt": "trace_sha256",
    "config.txt": "config_sha256",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with open(path, newline="") as stream:
        return list(csv.DictReader(stream))


def one_row(path):
    data = rows(path)
    if len(data) != 1:
        raise ValueError("%s expected exactly one row" % path)
    return data[0]


def parse_config(path):
    result = {}
    for line in path.read_text().splitlines():
        parts = line.split()
        if parts and not parts[0].startswith("#"):
            result[parts[0]] = " ".join(parts[1:])
    return result


def manifest():
    return rows(MANIFEST)


def ns(value):
    return int((Decimal(value) * Decimal(1000000000)).
               to_integral_value())


def metric_bundle(run):
    groups = rows(run / "group_round_summary.csv")
    flows = rows(run / "flow_summary.csv")
    rounds_data = rows(run / "round_summary.csv")
    queue = one_row(run / "queue_summary.csv")
    congestion = one_row(run / "congestion_summary.csv")
    wire = one_row(run / "wire_summary.csv")
    cfg = parse_config(run / "config.txt")
    if cfg.get("L2_ACK_INTERVAL") != "1":
        raise ValueError("ACK count equivalence requires L2_ACK_INTERVAL=1")
    data_count = int(wire["data_packet_count"])
    # The historical output has no control-packet trace. With loss disabled
    # and L2_ACK_INTERVAL=1, each received DATA packet generates one ACK, so
    # the DATA packet count is the exact modeled ACK count for this manifest.
    ack_count = data_count
    cnp_count = sum(int(row["cnp_count"]) for row in rounds_data)
    return {
        "group_rct_ns": {
            (row["group_id"], row["round_id"]): ns(row["group_rct"])
            for row in groups},
        "flow_fct_ns": {row["flow_id"]: ns(row["fct"]) for row in flows},
        "queue_max_bytes": int(Decimal(queue["queue_max_bytes"])),
        "ecn_marks": int(congestion["ecn_marks"]),
        "data_packet_count": data_count,
        "ack_packet_count": ack_count,
        "cnp_packet_count": cnp_count,
        "ack_count_basis": "L2_ACK_INTERVAL=1_lossless_DATA_equivalence",
    }


def compare(source, replay):
    old, new = metric_bundle(source), metric_bundle(replay)
    errors = []
    if old["group_rct_ns"].keys() != new["group_rct_ns"].keys():
        errors.append("group_key_set")
    else:
        delta = max([abs(old["group_rct_ns"][key] -
                         new["group_rct_ns"][key])
                     for key in old["group_rct_ns"]] or [0])
        if delta > 1:
            errors.append("group_rct_delta_gt_1ns")
    if old["flow_fct_ns"].keys() != new["flow_fct_ns"].keys():
        errors.append("flow_key_set")
    else:
        delta = max([abs(old["flow_fct_ns"][key] -
                         new["flow_fct_ns"][key])
                     for key in old["flow_fct_ns"]] or [0])
        if delta > 1:
            errors.append("flow_fct_delta_gt_1ns")
    if abs(old["queue_max_bytes"] - new["queue_max_bytes"]) > 1:
        errors.append("queue_max_delta_gt_1B")
    for key in ("ecn_marks", "data_packet_count", "ack_packet_count",
                "cnp_packet_count"):
        if old[key] != new[key]:
            errors.append(key)
    return errors


def validate_inputs(entry, run):
    errors = []
    source = SIM / entry["source_run"]
    if entry["scenario"] != "n32_64k_g50" or \
            entry["algorithm"] != "dcqcn" or entry["cc_mode"] != "1":
        errors.append("manifest_scope")
    for name, column in INPUT_MAP.items():
        if not (source / name).exists() or sha(source / name) != entry[column]:
            errors.append("source_" + name + "_hash")
        if not (run / name).exists() or sha(run / name) != entry[column]:
            errors.append("replay_" + name + "_hash")
    meta = json.load(open(source / "run_meta.json"))
    current_source = sha(SIM / "src/point-to-point/model/rdma-hw.cc")
    if meta.get("algorithm_source_hash") != \
            entry["algorithm_source_sha256"] or \
            current_source != entry["algorithm_source_sha256"]:
        errors.append("algorithm_source_hash")
    cfg = parse_config(run / "config.txt") if (run / "config.txt").exists() \
        else {}
    required = {
        "CC_MODE": "1", "PACKET_PAYLOAD_SIZE": "1000",
        "L2_ACK_INTERVAL": "1", "SIM_SEED": entry["seed"],
    }
    for key, value in required.items():
        if cfg.get(key) != value:
            errors.append("config_" + key)
    # These fields pin all DCQCN feedback/timer/recovery semantics.
    for key in ("KMIN_MAP", "KMAX_MAP", "PMAX_MAP", "BUFFER_SIZE",
                "USE_DYNAMIC_PFC_THRESHOLD", "ACK_HIGH_PRIO",
                "RATE_AI", "RATE_HAI", "ALPHA_RESUME_INTERVAL",
                "RP_TIMER", "EWMA_GAIN", "FAST_RECOVERY_TIMES",
                "RATE_DECREASE_INTERVAL", "MIN_RATE"):
        if key not in cfg:
            errors.append("config_missing_" + key)
    topology = (run / "topology.txt").read_text() \
        if (run / "topology.txt").exists() else ""
    if "100Gbps" not in topology:
        errors.append("link_rate")
    return sorted(set(errors))


def validate_output(entry, run):
    errors = validate_inputs(entry, run)
    required = (
        "completed.flag", "exit_status.txt", "run_meta.json",
        "group_round_summary.csv", "flow_summary.csv", "round_summary.csv",
        "queue_summary.csv", "congestion_summary.csv", "wire_summary.csv",
    )
    for name in required:
        if not (run / name).exists():
            errors.append("missing_" + name)
    if errors:
        return sorted(set(errors))
    if (run / "exit_status.txt").read_text().strip() != "0":
        errors.append("exit_status")
    meta = json.load(open(run / "run_meta.json"))
    if meta.get("log_truncated") or meta.get("scenario") != \
            entry["scenario"] or meta.get("algorithm") != entry["algorithm"]:
        errors.append("run_meta")
    errors.extend(compare(SIM / entry["source_run"], run))
    return sorted(set(errors))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", default=str(ROOT / "n32_dcqcn_replay"))
    parser.add_argument("--run")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--inputs-only", action="store_true")
    parser.add_argument("--static", action="store_true")
    args = parser.parse_args()
    entries = manifest()
    if len(entries) != 3 or {int(row["seed"]) for row in entries} != {1, 2, 3}:
        print("FAIL manifest_matrix")
        return 1
    if len({row["rounds_sha256"] for row in entries}) != 3:
        print("FAIL seed_jitter_hashes")
        return 1
    if args.static:
        errors = []
        for entry in entries:
            errors.extend(validate_inputs(
                entry, SIM / entry["source_run"]))
        if errors:
            print("FAIL", "|".join(sorted(set(errors))))
            return 1
        print("PASS n32 replay manifest seeds=1,2,3 exact_sources")
        return 0
    if args.run:
        if args.seed not in (1, 2, 3):
            print("FAIL seed")
            return 1
        entry = next(row for row in entries
                     if int(row["seed"]) == args.seed)
        errors = (validate_inputs(entry, Path(args.run)) if args.inputs_only
                  else validate_output(entry, Path(args.run)))
        if errors:
            print("FAIL seed=%d %s" % (args.seed, "|".join(errors)))
            return 1
        print("PASS seed=%d" % args.seed)
        return 0
    failures = []
    root = Path(args.runs)
    for entry in entries:
        seed = int(entry["seed"])
        errors = validate_output(entry, root / ("seed_%d" % seed))
        if errors:
            failures.append("seed=%d:%s" % (seed, "|".join(errors)))
    if failures:
        print("FAIL", ";".join(failures))
        return 1
    print("PASS n32 deterministic replay seeds=1,2,3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
