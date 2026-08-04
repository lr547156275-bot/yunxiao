#!/usr/bin/env python3
"""Write per-seed exact replay deltas; never uses the legacy 213-us run."""
import argparse
import csv
from pathlib import Path
from check_n32_dcqcn_replay import (
    SIM, compare, manifest, metric_bundle, sha)

ROOT = Path(__file__).resolve().parents[1]


def max_delta(left, right, key):
    return max([abs(left[key][item] - right[key][item])
                for item in left[key]] or [0])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", default=str(ROOT / "n32_dcqcn_replay"))
    parser.add_argument("--output",
                        default=str(ROOT / "analysis/n32_dcqcn_replay.csv"))
    args = parser.parse_args()
    run_root = Path(args.runs)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "scenario", "algorithm", "seed", "source_run", "replay_run",
        "input_hashes_exact", "config_hash_exact", "source_hash_exact",
        "max_group_rct_delta_ns", "max_flow_fct_delta_ns",
        "queue_max_delta_bytes", "ecn_old", "ecn_replay",
        "data_packets_old", "data_packets_replay",
        "ack_packets_old", "ack_packets_replay",
        "cnp_packets_old", "cnp_packets_replay", "ack_count_basis",
        "deterministic_pass", "failure_reason",
    ]
    output_rows = []
    failed = False
    for entry in manifest():
        seed = int(entry["seed"])
        source = SIM / entry["source_run"]
        replay = run_root / ("seed_%d" % seed)
        old, new = metric_bundle(source), metric_bundle(replay)
        input_exact = all(
            sha(source / name) == sha(replay / name)
            for name in ("topology.txt", "flow.txt", "rounds.txt",
                         "fixed_paths.txt", "trace.txt"))
        reasons = compare(source, replay)
        row = {
            "scenario": entry["scenario"], "algorithm": entry["algorithm"],
            "seed": seed, "source_run": entry["source_run"],
            "replay_run": str(replay.relative_to(SIM)),
            "input_hashes_exact": int(input_exact),
            "config_hash_exact": int(sha(source / "config.txt") ==
                                     sha(replay / "config.txt")),
            "source_hash_exact": int(sha(
                SIM / "src/point-to-point/model/rdma-hw.cc") ==
                entry["algorithm_source_sha256"]),
            "max_group_rct_delta_ns": max_delta(
                old, new, "group_rct_ns"),
            "max_flow_fct_delta_ns": max_delta(old, new, "flow_fct_ns"),
            "queue_max_delta_bytes": abs(
                old["queue_max_bytes"] - new["queue_max_bytes"]),
            "ecn_old": old["ecn_marks"], "ecn_replay": new["ecn_marks"],
            "data_packets_old": old["data_packet_count"],
            "data_packets_replay": new["data_packet_count"],
            "ack_packets_old": old["ack_packet_count"],
            "ack_packets_replay": new["ack_packet_count"],
            "cnp_packets_old": old["cnp_packet_count"],
            "cnp_packets_replay": new["cnp_packet_count"],
            "ack_count_basis": old["ack_count_basis"],
            "deterministic_pass": int(not reasons),
            "failure_reason": "|".join(reasons),
        }
        if reasons:
            failed = True
        output_rows.append(row)
    with open(output, "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)
    print(output)
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
