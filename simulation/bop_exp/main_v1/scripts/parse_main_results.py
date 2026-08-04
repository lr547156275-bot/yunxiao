#!/usr/bin/env python3
import argparse
import csv
import os
from mainlib import CONFIG, ROOT, rows
from check_main_outputs import validate_run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", default=os.path.join(ROOT, "runs"))
    parser.add_argument("--output", default=os.path.join(ROOT, "results"))
    args = parser.parse_args()
    os.makedirs(args.output, exist_ok=True)
    valid, invalid = [], []
    manifest = rows(os.path.join(CONFIG, "run_manifest.csv"))
    for item in manifest:
        run_dir = os.path.join(args.runs, item["scenario"], item["algorithm"],
                               "seed_%s" % item["seed"])
        errors = validate_run(run_dir)
        if errors:
            invalid.append({"run_id": item["run_id"],
                            "reason": "; ".join(errors)})
            continue
        pieces = {}
        for name in ("algorithm_summary.csv", "queue_summary.csv",
                     "congestion_summary.csv", "wire_summary.csv"):
            with open(os.path.join(run_dir, name), newline="") as handle:
                pieces.update(next(csv.DictReader(handle)))
        pieces["run_id"] = item["run_id"]
        pieces["section"] = item["section"]
        valid.append(pieces)
    summary = os.path.join(args.output, "summary.csv")
    fields = sorted({key for row in valid for key in row})
    with open(summary, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(valid)
    with open(os.path.join(args.output, "invalid_runs.csv"), "w",
              newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["run_id", "reason"])
        writer.writeheader()
        writer.writerows(invalid)
    print("valid=%d invalid=%d output=%s" % (
        len(valid), len(invalid), summary))


if __name__ == "__main__":
    main()
