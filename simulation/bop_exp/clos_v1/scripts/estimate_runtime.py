#!/usr/bin/env python3
import argparse
import csv
import os
import statistics

from closlib import CONFIG

parser = argparse.ArgumentParser()
parser.add_argument("--runs-root", default=os.path.join(
    os.path.dirname(CONFIG), "runs"))
parser.add_argument("--seeds", default="1,2,3")
args = parser.parse_args()
wanted = set(args.seeds.split(","))
manifest = list(csv.DictReader(open(os.path.join(CONFIG, "run_manifest.csv"))))
selected = [row for row in manifest if row["seed"] in wanted]
observed = []
for row in manifest:
    path = os.path.join(args.runs_root, row["run_id"], "runtime_seconds.txt")
    if os.path.exists(path):
        try:
            observed.append(float(open(path).read()))
        except ValueError:
            pass
estimate = statistics.median(observed) if observed else 0
print("selected_runs=%d completed_runtime_samples=%d" %
      (len(selected), len(observed)))
if estimate:
    print("median_seconds_per_run=%.1f serial_hours_estimate=%.2f" %
          (estimate, estimate * len(selected) / 3600.0))
else:
    print("serial_hours_estimate=UNKNOWN (no completed Clos run)")
