#!/usr/bin/env python3
import csv
import os
from mainlib import CONFIG, MAIN_ALGOS, ROOT, rows


def add(output, seen, section, scenario, algorithm, seed):
    run_id = "%s__%s__seed%d" % (scenario, algorithm, seed)
    if run_id in seen:
        raise RuntimeError("duplicate run_id: " + run_id)
    seen.add(run_id)
    output.append({"run_id": run_id, "section": section,
                   "scenario": scenario, "algorithm": algorithm,
                   "seed": seed})


def main():
    output, seen = [], set()
    mains = rows(os.path.join(CONFIG, "main_scenarios.csv"))
    ablations = rows(os.path.join(CONFIG, "ablation_scenarios.csv"))
    fairness = rows(os.path.join(CONFIG, "wire_fairness_manifest.csv"))
    for seed in (1, 2, 3):
        for spec in mains:
            for algorithm in MAIN_ALGOS:
                add(output, seen, "main", spec["scenario"], algorithm, seed)
        for spec in ablations:
            for algorithm in spec["algorithms"].split("|"):
                add(output, seen, "ablation", spec["scenario"], algorithm, seed)
        for spec in fairness:
            add(output, seen, "wire_fairness", spec["scenario"],
                spec["algorithm"], seed)
    path = os.path.join(CONFIG, "run_manifest.csv")
    with open(path, "w", newline="") as handle:
        fields = ["run_id", "section", "scenario", "algorithm", "seed"]
        writer = csv.DictWriter(handle, fieldnames=fields,
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(output)
    print("wrote %d unique runs to %s" % (len(output), path))


if __name__ == "__main__":
    main()
