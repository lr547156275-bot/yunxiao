#!/usr/bin/env python3
import argparse
import csv
import os
import re
import statistics
from mainlib import CONFIG, rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--seeds", default="1")
    args = parser.parse_args()
    seeds = {int(x) for x in args.seeds.split(",") if x}
    count = sum(int(x["seed"]) in seeds for x in rows(
        os.path.join(CONFIG, "run_manifest.csv")))
    observed = []
    if args.runs and os.path.isdir(args.runs):
        for root, _, files in os.walk(args.runs):
            if "runtime_seconds.txt" in files:
                try:
                    observed.append(float(open(os.path.join(
                        root, "runtime_seconds.txt")).read()))
                except ValueError:
                    pass
    if observed:
        seconds = statistics.median(observed) * count / max(args.jobs, 1)
        source = "median of %d completed runs" % len(observed)
    else:
        seconds = None
        source = "no completed runtime samples"
    print("runs=%d jobs=%d source=%s" % (count, args.jobs, source))
    if seconds is not None:
        print("estimated_wall_hours=%.2f" % (seconds / 3600))


if __name__ == "__main__":
    main()
