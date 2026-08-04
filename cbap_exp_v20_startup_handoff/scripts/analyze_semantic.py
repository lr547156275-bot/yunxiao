#!/usr/bin/env python3
import csv
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NAMES = {"0": "C0_NO_RISK", "1": "C1_SINGLE_HOTSPOT",
         "2": "C2_COMPLEX"}


def read_csv(path):
    with open(path, newline="") as stream:
        return list(csv.DictReader(stream))


def main():
    manifest = list(csv.DictReader(open(os.path.join(
        ROOT, "configs", "semantic_manifest.csv"))))
    findings, table = [], []
    for item in manifest:
        run = os.path.join(ROOT, "runs_semantic", item["scenario"],
                           item["algorithm_name"], "seed_%s" % item["seed"])
        flag = os.path.isfile(os.path.join(run, "completed.flag"))
        if not flag:
            findings.append("%s missing valid completed.flag" % item["semantic_id"])
            continue
        batch = read_csv(os.path.join(run, "cbap_v20_batch.csv"))
        flow = read_csv(os.path.join(run, "cbap_v20_flow.csv"))
        classes = sorted(set(NAMES[row["classification"]] for row in batch))
        expected = item["expected"]
        passed = True
        if expected in NAMES.values():
            passed = classes == [expected]
        elif expected == "CONTROLLED_QUEUE_BUILD":
            eligible = [r for r in batch if int(r["Q0_bytes"]) <
                        int(r["Q_target_bytes"]) - 1064]
            passed = bool(eligible) and all(int(r["R_startup_bps"]) >=
                                            int(r["C_effective_bps"])
                                            for r in eligible)
        elif expected == "QUEUE_DRAIN":
            eligible = [r for r in batch if int(r["Q0_bytes"]) >
                        int(r["Q_target_bytes"])]
            passed = bool(eligible) and all(int(r["R_startup_bps"]) <
                                            int(r["C_effective_bps"])
                                            for r in eligible)
        elif expected == "FRESH_FEEDBACK_HANDOFF":
            eligible = [r for r in batch if r["classification"] != "0"]
            passed = bool(eligible) and all(int(r["handoff_ns"]) > 0 and
                         int(r["first_fresh_feedback_ns"]) > 0 and
                         int(r["post_handoff_cbap_write_count"]) == 0 and
                         r["catch_up_burst"].lower() in ("0", "false")
                         for r in eligible)
        passed = passed and all(int(r["post_handoff_cbap_write_count"]) == 0
                                for r in flow)
        table.append((item["semantic_id"], item["scenario"], expected,
                      ";".join(classes), "PASS" if passed else "FAIL"))
        if not passed:
            findings.append("%s semantic predicate failed" % item["semantic_id"])
    report = os.path.join(ROOT, "reports", "semantic_results.md")
    with open(report, "w") as stream:
        stream.write("# CBAP-v2.0 semantic results\n\n")
        stream.write("| Test | Scenario | Expected | Observed | Status |\n")
        stream.write("|---|---|---|---|---|\n")
        for row in table:
            stream.write("| %s | %s | %s | %s | %s |\n" % row)
        stream.write("\nOverall: **%s**\n" %
                     ("PASS" if len(table) == 8 and not findings else "FAIL"))
        if findings:
            stream.write("\n## Findings\n\n" +
                         "".join("- %s\n" % x for x in findings))
    if len(table) != 8 or findings:
        raise SystemExit("semantic validation failed")
    print("SEMANTIC_PASS runs=8")


if __name__ == "__main__":
    main()
