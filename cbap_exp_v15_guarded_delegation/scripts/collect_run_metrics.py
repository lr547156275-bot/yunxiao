#!/usr/bin/env python3
"""Collect v1.5 metrics over the preregistered pending collective only.

Incumbent flows remain real network workload, but their completion time is not
part of collective completion or goodput. This prevents a long-lived incumbent
from either invalidating a correct collective run or dominating group RCT.
"""
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


def percentile(values, fraction):
    if not values:
        return 0.0
    data = sorted(values)
    index = (len(data) - 1) * fraction
    lo, hi = int(math.floor(index)), int(math.ceil(index))
    if lo == hi:
        return data[lo]
    return data[lo] + (data[hi] - data[lo]) * (index - lo)


def load_schedule(run_dir):
    schedule = {}
    with open(os.path.join(run_dir, "rounds.txt")) as stream:
        next(stream)
        for line in stream:
            fields = line.split()
            if fields:
                schedule[int(fields[0])] = int(fields[8]) / 1e9
    return schedule


def main(run_dir):
    meta = json.load(open(os.path.join(run_dir, "run_meta.json")))
    scenario = json.load(open(os.path.join(run_dir, "scenario_meta.json")))
    pending = set(int(x) for x in scenario.get("pending_flow_ids", []))
    incumbents = set(int(x) for x in scenario.get("incumbent_flow_ids", []))
    if not pending or pending & incumbents:
        raise SystemExit("invalid pending/incumbent flow registration")

    all_flow = rows(os.path.join(run_dir, "flow_summary.csv"))
    all_rounds = rows(os.path.join(run_dir, "round_summary.csv"))
    flow = [r for r in all_flow if int(r["flow_id"]) in pending]
    rounds = [r for r in all_rounds if int(r["flow_id"]) in pending]
    links = rows(os.path.join(run_dir, "selected_link_timeseries.csv"))
    pfc = rows(os.path.join(run_dir, "pfc_events.csv"))
    cbap = rows(os.path.join(run_dir, "cbap_flow_state.csv"))
    applied = rows(os.path.join(run_dir, "applied_rate_audit.csv"))
    schedule = load_schedule(run_dir)

    flow_by_id = {int(r["flow_id"]): r for r in flow}
    complete_ids = set(
        fid for fid, row in flow_by_id.items()
        if int(float(row.get("completed", 0))) == 1)
    round_ids = set(int(r["flow_id"]) for r in rounds)
    acked_round_ids = set(
        int(r["flow_id"]) for r in rounds
        if number(r, "ack_completion_time") > 0)
    all_pending_complete = (complete_ids == pending and
                            round_ids == pending and
                            acked_round_ids == pending)

    fcts, completion = [], []
    total_bytes = 0
    for row in flow:
        fid = int(row["flow_id"])
        finish = number(row, "finish_time")
        ready = schedule.get(fid, number(row, "start_time"))
        fcts.append(max(0.0, finish - ready))
        completion.append(finish)
        total_bytes += int(float(row["acked_bytes"]))

    grouped = {}
    for row in rounds:
        grouped.setdefault(int(row["round_group_id"]), []).append(row)
    group_rct = []
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
    pacing_violations = sum(int(float(row.get("pacing_violations", 0)))
                            for row in cbap)
    applied_violation_rows = sum(
        str(row.get("applied_capacity_violation", "0")).lower() in
        ("1", "true", "yes") for row in applied)
    applied_max_excess = max(
        (int(float(row.get("applied_capacity_excess_bps", 0) or 0))
         for row in applied), default=0)
    first = min((schedule[fid] for fid in pending), default=0)
    last = max(completion) if completion else first
    duration = max(last - first, 1e-12)
    result = {
        "scenario": meta["scenario"],
        "subcase": meta.get("subcase", meta["scenario"]),
        "algorithm": meta["algorithm"],
        "seed": meta["seed"],
        "metric_scope": "pending_collective_only",
        "expected_pending_flow_count": len(pending),
        "observed_pending_flow_count": len(flow_by_id),
        "completed_flow_count": len(complete_ids),
        "all_flows_completed": all_pending_complete,
        "all_pending_flows_completed": all_pending_complete,
        "incumbent_flow_count": len(incumbents),
        "completed_incumbent_flow_count": sum(
            int(r["flow_id"]) in incumbents and
            int(float(r.get("completed", 0))) == 1 for r in all_flow),
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
        "ecn_marks": int(ecn),
        "pfc_event_rows": len(pfc),
        "capacity_violations": violations,
        "credit_violations": credit_violations,
        "pacing_violations": pacing_violations,
        "applied_capacity_violation_rows": applied_violation_rows,
        "applied_capacity_max_excess_bps": applied_max_excess,
        "log_truncated": bool(meta.get("log_truncated", False)),
    }
    with open(os.path.join(run_dir, "result.json"), "w") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]))
