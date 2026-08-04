#!/usr/bin/env python3
import csv
import gzip
import json
import math
import os
import sys


def rows(path):
    if os.path.exists(path):
        with open(path, newline="") as stream:
            return list(csv.DictReader(stream))
    if os.path.exists(path + ".gz"):
        with gzip.open(path + ".gz", "rt", newline="") as stream:
            return list(csv.DictReader(stream))
    return []


def number(row, key, default=0.0):
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def percentile(values, p):
    if not values:
        return 0.0
    data = sorted(values)
    index = (len(data) - 1) * p
    lo, hi = int(math.floor(index)), int(math.ceil(index))
    if lo == hi:
        return data[lo]
    return data[lo] + (data[hi] - data[lo]) * (index - lo)


def main(run_dir):
    meta_path = os.path.join(run_dir, "run_meta.json")
    meta = json.load(open(meta_path))
    flow = rows(os.path.join(run_dir, "flow_summary.csv"))
    rounds = rows(os.path.join(run_dir, "round_summary.csv"))
    links = rows(os.path.join(run_dir, "selected_link_timeseries.csv"))
    pfc = rows(os.path.join(run_dir, "pfc_events.csv"))
    cbap = rows(os.path.join(run_dir, "cbap_flow_state.csv"))
    schedule = {}
    with open(os.path.join(run_dir, "rounds.txt")) as stream:
        next(stream)
        for line in stream:
            fields = line.split()
            if fields:
                schedule[int(fields[0])] = int(fields[8]) / 1e9
    fcts = []
    completion = []
    total_bytes = 0
    for row in flow:
        fid = int(row["flow_id"])
        finish = number(row, "finish_time")
        ready = schedule.get(fid, number(row, "start_time"))
        fcts.append(max(0.0, finish - ready))
        completion.append(finish)
        total_bytes += int(float(row["acked_bytes"]))
    group_rct = []
    grouped = {}
    for row in rounds:
        key = int(row["round_group_id"])
        grouped.setdefault(key, []).append(row)
    for group in grouped.values():
        ready = min(schedule[int(row["flow_id"])] for row in group)
        ack = max(number(row, "ack_completion_time") for row in group)
        group_rct.append(max(0.0, ack - ready))
    queues = [number(row, "queue_bytes") for row in links]
    util = [number(row, "utilization") for row in links]
    ecn = sum(number(row, "ecn_marks_delta") for row in links)
    violations = sum(int(float(row.get("capacity_violations", 0)))
                     for row in cbap)
    credit_violations = sum(int(float(row.get("credit_violations", 0)))
                            for row in cbap)
    first = min(schedule.values()) if schedule else 0
    last = max(completion) if completion else first
    duration = max(last - first, 1e-12)
    result = {
        "scenario": meta["scenario"],
        "subcase": meta.get("subcase", meta["scenario"]),
        "algorithm": meta["algorithm"], "seed": meta["seed"],
        "flow_count": len(flow),
        "completed_flow_count": sum(int(float(r["completed"])) for r in flow),
        "all_flows_completed": bool(flow) and
            all(int(float(r["completed"])) == 1 for r in flow),
        "flow_fct_mean_us": sum(fcts) / len(fcts) * 1e6 if fcts else 0,
        "flow_fct_max_us": max(fcts) * 1e6 if fcts else 0,
        "group_rct_mean_us":
            sum(group_rct) / len(group_rct) * 1e6 if group_rct else 0,
        "group_rct_max_us": max(group_rct) * 1e6 if group_rct else 0,
        "queue_max_bytes": max(queues) if queues else 0,
        "queue_p95_bytes": percentile(queues, 0.95),
        "queue_auc_byte_seconds": sum(queues) * 10e-6,
        "mean_utilization": sum(util) / len(util) if util else 0,
        "payload_goodput_gbps": total_bytes * 8 / duration / 1e9,
        "ecn_marks": int(ecn), "pfc_event_rows": len(pfc),
        "capacity_violations": violations,
        "credit_violations": credit_violations,
        "log_truncated": bool(meta.get("log_truncated", False)),
    }
    with open(os.path.join(run_dir, "result.json"), "w") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]))
