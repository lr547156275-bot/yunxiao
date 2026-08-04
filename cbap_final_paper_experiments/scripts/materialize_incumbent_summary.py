#!/usr/bin/env python3
"""Create the collector's incumbent ledger from existing low-rate artifacts."""
import csv
import gzip
import json
import os
import sys


def read_rows(run, name):
    for path in (os.path.join(run, name), os.path.join(run, name + ".gz")):
        if os.path.isfile(path):
            opener = gzip.open if path.endswith(".gz") else open
            with opener(path, "rt", newline="") as stream:
                return list(csv.DictReader(stream))
    return []


def number(value, default=0):
    try: return float(value)
    except (TypeError, ValueError): return default


def main(run):
    meta = json.load(open(os.path.join(run, "scenario_meta.json")))
    incumbent_ids = set(int(x) for x in meta.get("incumbent_flow_ids", []))
    summaries = {int(float(r["flow_id"])): r for r in read_rows(run, "flow_summary.csv")}
    rates = {int(float(r["flow_id"])): r for r in read_rows(run, "rate_summary.csv")}
    flow_lines = [line.split() for line in open(os.path.join(run, "flow.txt")) if line.split()][1:]
    fields = ["flow_id", "planned_bytes", "delivered_bytes", "acked_bytes",
              "remaining_bytes", "finished", "completion_time_seconds"]
    rows = []
    for fid in sorted(incumbent_ids):
        planned = int(flow_lines[fid][4]); summary = summaries.get(fid, {})
        rate = rates.get(fid, {})
        delivered = int(number(summary.get("acked_bytes"), 0))
        if rate.get("final_sample_remaining_bytes") not in (None, ""):
            delivered = max(delivered, planned - int(number(
                rate.get("final_sample_remaining_bytes"), planned)))
        finished = str(summary.get("completed", "0")).lower() in ("1", "true")
        if finished: delivered = planned
        rows.append({"flow_id": fid, "planned_bytes": planned,
                     "delivered_bytes": min(delivered, planned),
                     "acked_bytes": min(delivered, planned),
                     "remaining_bytes": max(planned - delivered, 0),
                     "finished": int(finished),
                     "completion_time_seconds": summary.get("finish_time", "")})
    with open(os.path.join(run, "incumbent_summary.csv"), "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


if __name__ == "__main__": main(os.path.abspath(sys.argv[1]))
