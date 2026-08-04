#!/usr/bin/env python3
"""Create immutable v1 case copies and the 20/84 run manifests."""
import csv
import hashlib
import json
import os
import shutil


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(ROOT, ".."))
SOURCE = os.path.join(REPO, "cbap_exp", "cases")
SCENARIOS = (
    ("e1_single_old_single_new", "default"),
    ("e2_batch_incast", "default"),
    ("e4_parking_lot", "synchronous"),
    ("e4_parking_lot", "staggered"),
)
MODES = {
    "dcqcn": 1, "hpcc_int": 3, "bop_qb": 15,
    "independent_min_grant": 20, "cbap_init_only": 21,
    "cbap_rate_only": 22, "cbap_full": 23,
}
SEMANTIC = (
    "dcqcn", "independent_min_grant", "cbap_init_only",
    "cbap_rate_only", "cbap_full",
)
FORMAL = tuple(MODES)


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def add_config_fields(path):
    fields = {
        "CBAP_TX_EVENT_FILE": "cbap_tx_events.csv",
        "CBAP_TX_TRACE_TRACKING_PACKETS": "4096",
    }
    lines = open(path).readlines()
    seen = set()
    output = []
    for line in lines:
        key = line.strip().split()[0] if line.strip() else ""
        if key in fields:
            output.append("%s %s\n" % (key, fields[key]))
            seen.add(key)
        else:
            output.append(line)
    for key in sorted(set(fields) - seen):
        output.append("%s %s\n" % (key, fields[key]))
    with open(path, "w") as stream:
        stream.writelines(output)


def write_manifest(path, algorithms, seeds, formal):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fields = ("run_id", "scenario", "subcase", "algorithm", "cc_mode",
              "seed", "formal")
    with open(path, "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for scenario, subcase in SCENARIOS:
            for algorithm in algorithms:
                for seed in seeds:
                    writer.writerow({
                        "run_id": "%s__%s__%s__seed%d" %
                                  (scenario, subcase, algorithm, seed),
                        "scenario": scenario, "subcase": subcase,
                        "algorithm": algorithm,
                        "cc_mode": MODES[algorithm], "seed": seed,
                        "formal": int(formal),
                    })


def main():
    case_root = os.path.join(ROOT, "cases")
    for scenario, subcase in SCENARIOS:
        source = os.path.join(SOURCE, scenario, subcase)
        destination = os.path.join(case_root, scenario, subcase)
        os.makedirs(destination, exist_ok=True)
        for name in os.listdir(source):
            source_path = os.path.join(source, name)
            if os.path.isfile(source_path):
                shutil.copy2(source_path, os.path.join(destination, name))
        add_config_fields(os.path.join(destination, "config.txt"))
        hashes = {}
        for name in sorted(os.listdir(destination)):
            path = os.path.join(destination, name)
            if os.path.isfile(path) and name != "input_hashes_v1.json":
                hashes[name] = digest(path)
        with open(os.path.join(destination, "input_hashes_v1.json"),
                  "w") as stream:
            json.dump(hashes, stream, indent=2, sort_keys=True)
            stream.write("\n")
    write_manifest(os.path.join(ROOT, "config", "semantic_manifest.csv"),
                   SEMANTIC, (1,), False)
    write_manifest(os.path.join(ROOT, "config", "formal_manifest.csv"),
                   FORMAL, (1, 2, 3), True)
    print("generated cases=%d semantic=20 formal=84" % len(SCENARIOS))


if __name__ == "__main__":
    main()
