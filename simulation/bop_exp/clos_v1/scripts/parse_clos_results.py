#!/usr/bin/env python3
import argparse
import csv
import gzip
import json
import math
import os
import statistics

from closlib import (BOP_PACKET_BYTES, ECN_THRESHOLD_BYTES, LINK_BPS,
                     PACKET_PAYLOAD_BYTES, percentile, read_csv)

HEADER_BYTES = {"dctcp": 48, "dcqcn": 48, "timely": 56,
                "hpcc_int": 90, "bop_qb": 90}


def number(row, key, default=0.0):
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def maybe_csv(path):
    if os.path.exists(path):
        return read_csv(path)
    if os.path.exists(path + ".gz"):
        with gzip.open(path + ".gz", "rt", newline="") as handle:
            return list(csv.DictReader(handle))
    return []


def write(path, fields, rows):
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields,
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_paths(run_dir):
    rows = {}
    with open(os.path.join(run_dir, "multilink_paths.txt")) as handle:
        count = int(handle.readline())
        for _ in range(count):
            values = [int(value) for value in handle.readline().split()]
            rows[values[0]] = values[2:]
    return rows


def load_links(run_dir):
    values = {}
    with open(os.path.join(run_dir, "multilink_links.txt")) as handle:
        count = int(handle.readline())
        for _ in range(count):
            row = [int(value) for value in handle.readline().split()]
            values[row[0]] = {
                "node_id": row[1], "if_index": row[2],
                "capacity_bps": row[3], "ecn_threshold_bytes": row[4],
                "background_bps": row[5],
                "telemetry_eligible": bool(row[6]),
            }
    return values


def aggregate(run_dir):
    meta = json.load(open(os.path.join(run_dir, "run_meta.json")))
    groups = read_csv(os.path.join(run_dir, "group_round_summary.csv"))
    rounds = read_csv(os.path.join(run_dir, "round_summary.csv"))
    schedule = read_csv(os.path.join(run_dir, "collective_schedule.csv"))
    links = maybe_csv(os.path.join(run_dir, "selected_link_timeseries.csv"))
    paths = load_paths(run_dir)
    link_definitions = load_links(run_dir)
    multi_groups = (read_csv(os.path.join(
        run_dir, "bop_multilink_group_decisions.csv"))
        if meta["algorithm"] == "bop_qb" else [])
    multi_links = (read_csv(os.path.join(
        run_dir, "bop_multilink_link_constraints.csv"))
        if meta["algorithm"] == "bop_qb" else [])

    group_by_id = {int(row["group_id"]): row for row in groups}
    schedule_by_id = {int(row["group_id"]): row for row in schedule}
    starts = [number(row, "common_release_time") for row in groups]
    finishes = [number(row, "barrier_completion_time") for row in groups]
    first, last = min(starts), max(finishes)
    active_seconds = max(last - first, 1e-15)
    rcts_us = [number(row, "group_rct") * 1e6 for row in groups]
    total_payload = sum(int(row["total_payload_bytes"]) for row in schedule)
    packet_count = sum((int(row["round_bytes"]) +
                        PACKET_PAYLOAD_BYTES - 1) //
                       PACKET_PAYLOAD_BYTES for row in rounds)
    wire_bytes = total_payload + packet_count * HEADER_BYTES[meta["algorithm"]]
    path_hop_bytes = 0
    path_load = {}
    for row in rounds:
        flow_id, amount = int(row["flow_id"]), int(row["round_bytes"])
        path_hop_bytes += amount * len(paths[flow_id])
        for link_id in paths[flow_id]:
            path_load[link_id] = path_load.get(link_id, 0) + amount
    capacity_time = active_seconds * LINK_BPS / 8
    group_link_work = {}
    for row in rounds:
        group_id = int(row["round_group_id"])
        amount = int(row["round_bytes"])
        for link_id in paths[int(row["flow_id"])]:
            key = (group_id, link_id)
            group_link_work[key] = group_link_work.get(key, 0) + amount

    link_samples = {}
    ecn_total = 0
    for row in links:
        when = number(row, "time")
        if when < first or when > last:
            continue
        link_id = row["link_id"]
        link_samples.setdefault(link_id, []).append(row)
        ecn_total += int(number(row, "ecn_marks_delta"))
    per_link = []
    sample_us = 100.0
    for link_id, samples in sorted(link_samples.items()):
        queues = [number(row, "queue_bytes") for row in samples]
        utils = [number(row, "utilization") for row in samples]
        per_link.append({
            "link_id": link_id,
            "utilization_mean": statistics.mean(utils),
            "utilization_p95": percentile(utils, .95),
            "utilization_max": max(utils),
            "queue_p95_bytes": percentile(queues, .95),
            "queue_max_bytes": max(queues),
            "time_above_ecn_us":
                sum(value >= ECN_THRESHOLD_BYTES for value in queues) *
                sample_us,
        })
    represented = set(row["link_id"] for row in per_link)
    for link_id, definition in sorted(link_definitions.items()):
        label = "%d:%d" % (definition["node_id"], definition["if_index"])
        if label in represented:
            continue
        work, duration = 0, 0.0
        for (group_id, candidate), amount in group_link_work.items():
            if candidate != link_id or group_id not in group_by_id:
                continue
            work += amount
            duration += number(group_by_id[group_id], "group_rct")
        per_link.append({
            "link_id": label,
            "utilization_mean": (work * 8 /
                                 max(duration * definition["capacity_bps"], 1)),
            "utilization_p95": "NA", "utilization_max": "NA",
            "queue_p95_bytes": "NA", "queue_max_bytes": "NA",
            "time_above_ecn_us": "NA",
        })
    sampled_rows = [row for row in per_link
                    if row["queue_max_bytes"] != "NA"]
    queue_max = max([row["queue_max_bytes"] for row in sampled_rows] or [0])
    queue_p95 = max([row["queue_p95_bytes"] for row in sampled_rows] or [0])
    utils_mean = [row["utilization_mean"] for row in per_link]
    utils_p95 = [row["utilization_p95"] for row in per_link
                 if row["utilization_p95"] != "NA"]
    utils_max = [row["utilization_max"] for row in per_link
                 if row["utilization_max"] != "NA"]

    # Static lower bound replays q=0 multi-link workload constraints.
    round_by_group = {}
    for row in rounds:
        round_by_group.setdefault(int(row["round_group_id"]), []).append(row)
    static_lower = []
    for group_id, members in round_by_group.items():
        workloads = {}
        line = 0
        for row in members:
            amount = int(row["round_bytes"])
            line = max(line, 8.0 * amount / LINK_BPS)
            for link_id in paths[int(row["flow_id"])]:
                workloads[link_id] = workloads.get(link_id, 0) + amount
        static_lower.append(max(
            [line] + [8.0 * amount / LINK_BPS
                      for amount in workloads.values()]))
    mean_lower_us = statistics.mean(static_lower) * 1e6
    mean_rct_us = statistics.mean(rcts_us)

    stage_groups = {}
    iteration_groups = {}
    collective_rows = []
    for group_id, row in schedule_by_id.items():
        if group_id not in group_by_id:
            continue
        rct = number(group_by_id[group_id], "group_rct") * 1e6
        stage_groups.setdefault((row["iteration"], row["stage"]), []).append(rct)
        iteration_groups.setdefault(row["iteration"], []).append(
            group_by_id[group_id])
    for (iteration, stage), values in sorted(stage_groups.items()):
        collective_rows.append({
            "iteration": iteration, "stage": stage,
            "collective_completion_mean_us": statistics.mean(values),
            "collective_completion_p95_us": percentile(values, .95),
            "collective_completion_max_us": max(values),
            "step_completion_mean_us": statistics.mean(values),
            "slowest_step_us": max(values),
        })
    iteration_times = []
    skews = []
    for iteration, values in sorted(iteration_groups.items()):
        releases = [number(row, "common_release_time") for row in values]
        barriers = [number(row, "barrier_completion_time") for row in values]
        iteration_times.append((max(barriers) - min(releases)) * 1e6)
        skews.append((max(barriers) - min(barriers)) * 1e6)

    limiting = [row for row in multi_links
                if row.get("limiting_link") == "1"]
    formula_errors = sum(
        row.get("formula_valid") != "1" or
        row.get("capacity_valid") != "1" or
        row.get("credit_constraint_valid") != "1"
        for row in multi_links + multi_groups)
    capacity_violations = sum(
        row.get("capacity_valid") != "1" for row in multi_links)
    credit_violations = sum(
        row.get("credit_constraint_valid") != "1" for row in multi_links)
    alphas = [number(row, "alpha") for row in multi_groups]
    tstars = [number(row, "T_star_us") for row in multi_groups]
    hot = sum(value >= .90 for value in utils_mean)
    collisions = sum(max(count - 1, 0)
                     for count in {
                         link: sum(link in path for path in paths.values())
                         for link in set(x for path in paths.values()
                                         for x in path)}.values())
    row = {
        "scenario": meta["scenario"], "algorithm": meta["algorithm"],
        "seed": meta["seed"],
        "collective_completion_mean_us": mean_rct_us,
        "collective_completion_p95_us": percentile(rcts_us, .95),
        "collective_completion_max_us": max(rcts_us),
        "step_completion_mean_us": mean_rct_us,
        "slowest_step_us": max(rcts_us),
        "iteration_completion_us": statistics.mean(iteration_times),
        "total_sequence_completion_us": active_seconds * 1e6,
        "theoretical_lower_bound_us": mean_lower_us,
        "lower_bound_efficiency": mean_lower_us / mean_rct_us,
        "completion_skew_us": statistics.mean(skews),
        "payload_goodput_gbps": total_payload * 8 / active_seconds / 1e9,
        "wire_throughput_gbps": wire_bytes * 8 / active_seconds / 1e9,
        "active_payload_utilization":
            path_hop_bytes / max(capacity_time * len(path_load), 1),
        "per_link_utilization_mean":
            statistics.mean(utils_mean) if utils_mean else 0,
        "per_link_utilization_p95":
            percentile(utils_p95, .95) if utils_p95 else 0,
        "per_link_utilization_max": max(utils_max) if utils_max else 0,
        "hot_link_count": hot, "limiting_link_count": len(limiting),
        "path_collision_count": collisions,
        "global_queue_max_bytes": queue_max,
        "per_link_queue_p95_max_bytes": queue_p95,
        "time_above_ecn_us": sum(
            row["time_above_ecn_us"] for row in per_link
            if row["time_above_ecn_us"] != "NA"),
        "ecn_marks": ecn_total,
        "ecn_per_1000_data": (ecn_total * 1000.0 / packet_count
                              if packet_count else 0),
        "pfc_events": "NA", "dropped_packets": "NA",
        "retransmitted_packets": "NA",
        "T_star_us": statistics.mean(tstars) if tstars else "NA",
        "alpha": statistics.mean(alphas) if alphas else "NA",
        "capacity_violations": capacity_violations,
        "credit_constraint_violations": credit_violations,
        "formula_replay_errors": formula_errors,
    }
    write(os.path.join(run_dir, "run_metrics.csv"), list(row), [row])
    fields = list(per_link[0]) if per_link else [
        "link_id", "utilization_mean", "utilization_p95",
        "utilization_max", "queue_p95_bytes", "queue_max_bytes",
        "time_above_ecn_us"]
    write(os.path.join(run_dir, "per_link_metrics.csv"), fields, per_link)
    fields = list(collective_rows[0]) if collective_rows else [
        "iteration", "stage", "collective_completion_mean_us",
        "collective_completion_p95_us", "collective_completion_max_us",
        "step_completion_mean_us", "slowest_step_us"]
    write(os.path.join(run_dir, "collective_metrics.csv"),
          fields, collective_rows)
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run")
    parser.add_argument("--root")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.run:
        aggregate(os.path.abspath(args.run))
        return
    if not args.root or not args.output:
        parser.error("use --run or --root plus --output")
    rows = []
    for current, _dirs, files in os.walk(args.root):
        if "completed.flag" in files:
            rows.append(aggregate(current))
    if rows:
        write(args.output, list(rows[0]), rows)


if __name__ == "__main__":
    main()
