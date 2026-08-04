#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
import math
import os


def rows(path):
    with open(path, newline="") as stream:
        return list(csv.DictReader(stream))


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    parser.add_argument("--allow-no-complete-flag", action="store_true")
    parser.add_argument("--expected", default="MEASURE")
    args = parser.parse_args()
    run = os.path.abspath(args.run_dir)
    required = ["run_meta.json", "flow_summary.csv", "round_summary.csv",
                "cbap_v20_batch.csv", "cbap_v20_flow.csv",
                "controller_ownership.csv", "result.json",
                "result_full_work.json", "metric_provenance.json",
                "flow_outcome_ledger.csv", "exit_status.txt"]
    missing = [name for name in required
               if not os.path.isfile(os.path.join(run, name))]
    if missing:
        raise SystemExit("missing outputs: %s" % ",".join(missing))
    if not args.allow_no_complete_flag and not os.path.isfile(
            os.path.join(run, "completed.flag")):
        raise SystemExit("missing completed.flag")
    if open(os.path.join(run, "exit_status.txt")).read().strip() != "0":
        raise SystemExit("non-zero exit status")
    meta = json.load(open(os.path.join(run, "run_meta.json")))
    if int(meta.get("cc_mode", -1)) not in (28, 29):
        raise SystemExit("wrong CC_MODE")
    if meta.get("algorithm_version") != "cbap_v20_startup_handoff":
        raise SystemExit("wrong algorithm version")
    if float(meta.get("queue_target_fraction", -1)) not in (
            0, .125, .25, .5, .75):
        raise SystemExit("invalid queue target fraction")
    expected_hashes = meta.get("input_hashes", {})
    if not expected_hashes:
        raise SystemExit("missing input hashes")
    for name, expected in expected_hashes.items():
        path = os.path.join(run, name)
        if not os.path.isfile(path) or sha256(path) != expected:
            raise SystemExit("input hash mismatch: %s" % name)
    flow = rows(os.path.join(run, "flow_summary.csv"))
    rounds = rows(os.path.join(run, "round_summary.csv"))
    batch = rows(os.path.join(run, "cbap_v20_batch.csv"))
    plans = rows(os.path.join(run, "cbap_v20_flow.csv"))
    if not flow or not rounds or not batch or not plans:
        raise SystemExit("empty required CSV")
    if any(str(row.get("completed", "")).lower() not in
           ("1", "true") for row in flow):
        raise SystemExit("not all flows completed")
    full = json.load(open(os.path.join(run, "result_full_work.json")))
    if not full.get("all_flows_completed", False):
        raise SystemExit("full-work collector reports incomplete flows")
    if not full.get("byte_conservation_valid", False):
        raise SystemExit("full-work byte conservation failed")
    for row in batch:
        for key in ("blind_window_ns", "Q0_bytes", "Q_target_bytes",
                    "C_effective_bps", "W_l_bytes", "S_l_bytes",
                    "E_l_bytes", "R_startup_bps"):
            value = float(row[key])
            if not math.isfinite(value) or value < 0:
                raise SystemExit("invalid batch value %s" % key)
        if row["capacity_violation"] not in ("0", "False", "false"):
            raise SystemExit("startup capacity prediction violation")
        if row["pacing_violation"] not in ("0", "False", "false"):
            raise SystemExit("startup pacing violation")
        if row["post_handoff_cbap_write_count"] != "0":
            raise SystemExit("post-handoff CBAP write")
        if row["catch_up_burst"] not in ("0", "False", "false"):
            raise SystemExit("catch-up burst")
    names = {"0": "C0_NO_RISK", "1": "C1_SINGLE_HOTSPOT",
             "2": "C2_COMPLEX"}
    classes = sorted(set(names[row["classification"]] for row in batch))
    expected = args.expected
    semantic_ok = True
    if expected in names.values():
        semantic_ok = classes == [expected]
    elif expected == "CONTROLLED_QUEUE_BUILD":
        eligible = [row for row in batch if int(row["Q0_bytes"]) <
                    int(row["Q_target_bytes"]) - 1064]
        semantic_ok = bool(eligible) and all(
            int(row["R_startup_bps"]) >= int(row["C_effective_bps"])
            for row in eligible)
    elif expected == "QUEUE_DRAIN":
        eligible = [row for row in batch if int(row["Q0_bytes"]) >
                    int(row["Q_target_bytes"])]
        semantic_ok = bool(eligible) and all(
            int(row["R_startup_bps"]) < int(row["C_effective_bps"])
            for row in eligible)
    elif expected == "FRESH_FEEDBACK_HANDOFF":
        eligible = [row for row in batch if row["classification"] != "0"]
        semantic_ok = bool(eligible) and all(
            int(row["handoff_ns"]) > 0 and
            int(row["first_fresh_feedback_ns"]) > 0 and
            int(row["post_handoff_cbap_write_count"]) == 0 and
            row["catch_up_burst"].lower() in ("0", "false")
            for row in eligible)
    if not semantic_ok:
        raise SystemExit("semantic predicate failed: %s" % expected)
    print("PASS %s" % run)


if __name__ == "__main__":
    main()
