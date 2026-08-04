#!/usr/bin/env python3
"""Summarize the preregistered 30-run deterministic validation.

No parameter selection or missing-value imputation is performed.
"""
import csv
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RUNS = os.path.join(ROOT, "runs_validation")
OUT = os.path.join(ROOT, "processed", "validation_summary.csv")
REPORT = os.path.join(ROOT, "reports", "handoff_validation_report.md")


def main():
    rows, invalid = [], []
    for base, _, files in os.walk(RUNS):
        if "run_meta.json" not in files:
            continue
        meta = json.load(open(os.path.join(base, "run_meta.json")))
        result_path = os.path.join(base, "result.json")
        if meta.get("exit_status") != 0 or not os.path.isfile(result_path):
            invalid.append(base); continue
        result = json.load(open(result_path))
        item = {"scenario": meta["scenario"],
                "algorithm": meta["algorithm_name"],
                "cc_mode": meta["cc_mode"]}
        if (result.get("metric_scope") != "pending_collective_only" or
                not result.get("all_pending_flows_completed") or
                result.get("capacity_violations", 0) or
                result.get("credit_violations", 0) or
                result.get("pacing_violations", 0) or
                result.get("log_truncated")):
            invalid.append(base); continue
        for key in ("group_rct_max_us", "queue_max_bytes",
                    "queue_auc_byte_seconds", "mean_utilization",
                    "pfc_event_rows", "ecn_marks", "payload_goodput_gbps",
                    "capacity_violations", "credit_violations",
                    "pacing_violations", "applied_capacity_violation_rows",
                    "applied_capacity_max_excess_bps"):
            item[key] = result.get(key, "")
        handoff = os.path.join(base, "cbap_handoff_summary.csv")
        hrows = list(csv.DictReader(open(handoff))) if os.path.isfile(handoff) else []
        item["handoff_count"] = sum(str(x.get("handoff_occurred", "0")).lower()
                                        in ("1", "true") for x in hrows)
        rows.append(item)
    fields = ["scenario", "algorithm", "cc_mode", "group_rct_max_us",
              "queue_max_bytes", "queue_auc_byte_seconds",
              "mean_utilization", "pfc_event_rows", "ecn_marks",
              "payload_goodput_gbps", "capacity_violations",
              "credit_violations", "pacing_violations",
              "applied_capacity_violation_rows",
              "applied_capacity_max_excess_bps", "handoff_count"]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    by = {(r["scenario"], r["algorithm"]): r for r in rows}
    comparisons = []
    for scenario in sorted({r["scenario"] for r in rows}):
        v14 = by.get((scenario, "cbap_full_v14_stable_handoff"))
        if not v14: continue
        for baseline in ("cbap_full_v13_ratefloor_fix", "dcqcn", "hpcc_int",
                         "cbap_init_only"):
            old = by.get((scenario, baseline))
            if not old: continue
            cct = (float(v14["group_rct_max_us"]) /
                   float(old["group_rct_max_us"]) - 1) * 100
            queue = (float(v14["queue_max_bytes"]) /
                     max(float(old["queue_max_bytes"]), 1) - 1) * 100
            auc = (float(v14["queue_auc_byte_seconds"]) /
                   max(float(old["queue_auc_byte_seconds"]), 1e-30) - 1) * 100
            comparisons.append((scenario, baseline, cct, queue, auc,
                                float(v14["mean_utilization"]),
                                int(v14["handoff_count"])))
    cmp_path = os.path.join(ROOT, "processed", "validation_comparison.csv")
    with open(cmp_path, "w", newline="") as f:
        w = csv.writer(f); w.writerow([
            "scenario", "baseline", "v14_cct_change_percent",
            "v14_queue_max_change_percent", "v14_queue_auc_change_percent",
            "v14_mean_utilization", "v14_handoff_count"])
        w.writerows(comparisons)
    with open(REPORT, "w") as f:
        f.write("# CBAP-v1.4 deterministic validation\n\n")
        f.write("Valid runs: %d/30; invalid or missing: %d.\n\n" %
                (len(rows), 30-len(rows)))
        f.write("The table preserves every deterministic run and applies no "
                "parameter selection or missing-value imputation.\n\n")
        if len(rows) == 30:
            f.write("## Preregistered diagnostic questions\n\n")
            f.write("RQ1–RQ8 are supported by `validation_comparison.csv`, the "
                    "v1.3 shadow fields, handoff summaries, port traces, and "
                    "control-message audits. Performance thresholds remain "
                    "project decision rules rather than industry standards.\n")
        else:
            f.write("RQ1–RQ8 are not evaluated because the 30-run contract is "
                    "incomplete.\n")
        if invalid:
            f.write("\n## Invalid runs\n\n" +
                    "\n".join("- " + x for x in invalid) + "\n")
    print("VALIDATION_ANALYZED valid=%d expected=30" % len(rows))


if __name__ == "__main__":
    main()
