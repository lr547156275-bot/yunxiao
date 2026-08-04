#!/usr/bin/env python3
"""Materialize the stable per-run queue/rate/control summary contract."""
import csv
import gzip
import os
import sys
from collections import defaultdict


def open_csv(path):
    if os.path.isfile(path):
        return open(path, newline="")
    if os.path.isfile(path + ".gz"):
        return gzip.open(path + ".gz", "rt", newline="")
    return None


def number(row, key):
    try:
        return float(row.get(key, 0))
    except (TypeError, ValueError):
        return 0.0


def write(path, fields, rows):
    with open(path, "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(run):
    source = open_csv(os.path.join(run, "selected_link_timeseries.csv"))
    link = defaultdict(lambda: {"samples": 0, "queue_sum": 0.0,
                                "queue_max": 0.0, "util_sum": 0.0,
                                "ecn": 0.0, "pfc": 0.0})
    if source:
        for row in csv.DictReader(source):
            item = link[row["link_id"]]
            queue = number(row, "queue_bytes")
            item["samples"] += 1
            item["queue_sum"] += queue
            item["queue_max"] = max(item["queue_max"], queue)
            item["util_sum"] += number(row, "utilization")
            item["ecn"] += number(row, "ecn_marks_delta")
            item["pfc"] += number(row, "pfc_event_delta")
        source.close()
    queue_rows = []
    for link_id, item in sorted(link.items()):
        count = item["samples"]
        queue_rows.append({
            "link_id": link_id, "sample_count": count,
            "queue_mean_bytes": item["queue_sum"] / count if count else 0,
            "queue_max_bytes": item["queue_max"],
            "utilization_mean": item["util_sum"] / count if count else 0,
            "ecn_marks": int(item["ecn"]),
            "pfc_events": int(item["pfc"]),
        })
    write(os.path.join(run, "queue_summary.csv"),
          ["link_id", "sample_count", "queue_mean_bytes",
           "queue_max_bytes", "utilization_mean", "ecn_marks",
           "pfc_events"], queue_rows)

    source = open_csv(os.path.join(run, "selected_flow_timeseries.csv"))
    flows = defaultdict(lambda: {"samples": 0, "min": None, "max": 0,
                                 "last": 0, "remaining_last": 0})
    if source:
        for row in csv.DictReader(source):
            fid = row["flow_id"]
            rate = number(row, "current_rate")
            item = flows[fid]
            item["samples"] += 1
            item["min"] = rate if item["min"] is None else min(
                item["min"], rate)
            item["max"] = max(item["max"], rate)
            item["last"] = rate
            item["remaining_last"] = number(row, "released_bytes") - \
                number(row, "snd_una")
        source.close()
    rate_rows = [{
        "flow_id": fid, "sample_count": item["samples"],
        "minimum_rate_bps": item["min"] or 0,
        "maximum_rate_bps": item["max"],
        "final_sample_rate_bps": item["last"],
        "final_sample_remaining_bytes": item["remaining_last"],
    } for fid, item in sorted(flows.items(), key=lambda pair:
                              int(pair[0]))]
    write(os.path.join(run, "rate_summary.csv"),
          ["flow_id", "sample_count", "minimum_rate_bps",
           "maximum_rate_bps", "final_sample_rate_bps",
           "final_sample_remaining_bytes"], rate_rows)

    overhead_path = os.path.join(run, "cbap_control_overhead.csv")
    control_rows = []
    if os.path.isfile(overhead_path):
        with open(overhead_path, newline="") as stream:
            control_rows = list(csv.DictReader(stream))
    if not control_rows:
        control_rows = [{
            "summary_messages": 0, "grant_messages": 0,
            "summary_bytes_each": 0, "grant_bytes_each": 0,
            "total_control_bytes": 0, "control_delay_ns": 0,
            "planning_delay_ns": 0,
        }]
    write(os.path.join(run, "control_summary.csv"),
          ["summary_messages", "grant_messages", "summary_bytes_each",
           "grant_bytes_each", "total_control_bytes", "control_delay_ns",
           "planning_delay_ns"], control_rows)


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]))
