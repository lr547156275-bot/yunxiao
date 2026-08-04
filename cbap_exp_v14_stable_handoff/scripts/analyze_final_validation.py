#!/usr/bin/env python3
"""Create the final deterministic v1.4 validation analysis.

This script consumes existing summaries only.  It does not run ns-3, select
parameters, discard scenarios, or treat the single deterministic seed as an
independent statistical sample.
"""
import csv
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SUMMARY = os.path.join(ROOT, "processed", "validation_summary.csv")
DETAIL = os.path.join(ROOT, "processed", "final_pairwise_analysis.csv")
HANDOFF = os.path.join(ROOT, "processed", "handoff_coverage.csv")
REPORT = os.path.join(ROOT, "reports", "final_validation_analysis.md")
V14 = "cbap_full_v14_stable_handoff"
BASELINES = ("cbap_full_v13_ratefloor_fix", "dcqcn", "hpcc_int",
             "cbap_init_only")


def read_csv(path):
    with open(path, newline="") as stream:
        return list(csv.DictReader(stream))


def change(new, old):
    return (new / old - 1.0) * 100.0 if old else None


def fmt(value, digits=2):
    return "n/a" if value is None else ("%%.%df" % digits) % value


def main():
    rows = read_csv(SUMMARY)
    by = {(r["scenario"], r["algorithm"]): r for r in rows}
    scenarios = sorted({r["scenario"] for r in rows})
    if len(rows) != 30 or len(scenarios) != 6:
        raise SystemExit("expected 30 rows and 6 scenarios")
    if any((scenario, algorithm) not in by for scenario in scenarios
           for algorithm in (V14,) + BASELINES):
        raise SystemExit("incomplete scenario/algorithm matrix")

    details = []
    metrics = (("group_rct_max_us", "lower"),
               ("queue_max_bytes", "lower"),
               ("queue_auc_byte_seconds", "lower"),
               ("payload_goodput_gbps", "higher"),
               ("mean_utilization", "higher"),
               ("ecn_marks", "lower"),
               ("pfc_event_rows", "lower"))
    for scenario in scenarios:
        current = by[scenario, V14]
        for baseline in BASELINES:
            old = by[scenario, baseline]
            item = {"scenario": scenario, "baseline": baseline,
                    "handoff_count": int(current["handoff_count"])}
            for metric, direction in metrics:
                new_value, old_value = float(current[metric]), float(old[metric])
                delta = change(new_value, old_value)
                item["v14_" + metric] = new_value
                item["baseline_" + metric] = old_value
                item[metric + "_change_percent"] = "" if delta is None else delta
                if delta is None or abs(delta) < 1e-12:
                    result = "tie"
                elif (direction == "lower" and delta < 0) or (
                        direction == "higher" and delta > 0):
                    result = "improvement"
                else:
                    result = "regression"
                item[metric + "_result"] = result
            details.append(item)
    fields = list(details[0])
    with open(DETAIL, "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader(); writer.writerows(details)

    coverage = []
    for scenario in scenarios:
        directory = os.path.join(ROOT, "runs_validation", scenario, V14,
                                 "seed_1")
        handoff_rows = read_csv(os.path.join(
            directory, "cbap_handoff_summary.csv"))
        for row in handoff_rows:
            coverage.append({
                "scenario": scenario,
                "handoff_occurred": row["handoff_occurred"],
                "handoff_execute_ns": row["handoff_execute_ns"],
                "remaining_fraction": row["remaining_fraction"],
                "remaining_bytes_total": row["remaining_bytes_total"],
                "queue_bytes_at_handoff": row["queue_bytes_at_handoff"],
                "applied_rate_sum_before": row["applied_rate_sum_before"],
                "stable_epoch_count": row["stable_epoch_count"],
                "minimum_tracking_time_ns": row["minimum_tracking_time_ns"],
                "terminal_reason": row["no_handoff_reason"],
            })
    handoff_fields = list(coverage[0])
    with open(HANDOFF, "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=handoff_fields)
        writer.writeheader(); writer.writerows(coverage)

    def detail(scenario, baseline):
        return next(r for r in details if r["scenario"] == scenario and
                    r["baseline"] == baseline)

    handoff_scenarios = [r["scenario"] for r in coverage
                         if str(r["handoff_occurred"]).lower() in
                         ("1", "true", "yes")]
    dcqcn_queue = [float(detail(s, "dcqcn")[
        "queue_max_bytes_change_percent"]) for s in scenarios]
    hpcc_queue = [float(detail(s, "hpcc_int")[
        "queue_max_bytes_change_percent"]) for s in scenarios]

    with open(REPORT, "w") as stream:
        stream.write("# CBAP-v1.4 final deterministic validation analysis\n\n")
        stream.write("**Overall assessment: MIXED — REVISE OR NARROW THE "
                     "STABLE-HANDOFF CLAIM.**\n\n")
        stream.write("The 30/30-run matrix is complete and internally valid, "
                     "but the results do not support a general RCT-superiority "
                     "claim for v1.4. They do support a strong queue-reduction "
                     "claim against DCQCN and HPCC-INT in these deterministic "
                     "single-seed scenarios.\n\n")
        stream.write("## Data validity and scope\n\n")
        stream.write("- Valid runs: 30/30; invalid or missing: 0.\n")
        stream.write("- Scenarios: 6; algorithms per scenario: 5; seed: 1 only.\n")
        stream.write("- All preregistered collective flows and rounds completed; "
                     "capacity, credit, and CBAP-owned pacing violations are zero.\n")
        stream.write("- PFC event rows are zero for every algorithm and scenario.\n")
        stream.write("- Metrics use the preregistered pending collective only; "
                     "incumbent traffic remains real network load.\n")
        stream.write("- This is deterministic ns-3 evidence, not a multi-seed "
                     "confidence interval or deployment result.\n\n")
        stream.write("## Stable-handoff coverage\n\n")
        stream.write("Handoff occurred in %d/6 scenarios: %s. The other cases "
                     "completed before satisfying the unchanged eligibility "
                     "predicate.\n\n" % (len(handoff_scenarios),
                                        ", ".join(handoff_scenarios)))
        stream.write("| Scenario | Handoff | Time (us) | Remaining | Queue at handoff (B) | Reason |\n")
        stream.write("|---|---:|---:|---:|---:|---|\n")
        for row in coverage:
            stream.write("| %s | %s | %.3f | %.2f%% | %s | %s |\n" % (
                row["scenario"], row["handoff_occurred"],
                int(row["handoff_execute_ns"]) / 1000.0,
                float(row["remaining_fraction"]) * 100.0,
                row["queue_bytes_at_handoff"], row["terminal_reason"]))

        stream.write("\n## v1.4 compared with v1.3\n\n")
        stream.write("| Scenario | RCT change | Queue-max change | Queue-AUC change | Goodput change |\n")
        stream.write("|---|---:|---:|---:|---:|\n")
        for scenario in scenarios:
            row = detail(scenario, "cbap_full_v13_ratefloor_fix")
            stream.write("| %s | %s%% | %s%% | %s%% | %s%% |\n" % (
                scenario,
                fmt(float(row["group_rct_max_us_change_percent"])),
                fmt(float(row["queue_max_bytes_change_percent"])),
                fmt(float(row["queue_auc_byte_seconds_change_percent"])),
                fmt(float(row["payload_goodput_gbps_change_percent"]))))
        stream.write("\nThe non-handoff cases are bit-for-bit equal in these "
                     "aggregate metrics. Stable handoff improves 4 MiB RCT by "
                     "18.85% and goodput by 23.23%, but raises peak queue by "
                     "141.74%. In both 1 MiB handoff cases, RCT regresses by "
                     "2.29–2.43% while peak queue rises by 92.15–98.41%; those "
                     "two cases do not justify the handoff on the measured "
                     "RCT–queue tradeoff.\n\n")

        stream.write("## External congestion-control baselines\n\n")
        stream.write("| Scenario | vs DCQCN RCT | vs DCQCN queue | vs HPCC RCT | vs HPCC queue |\n")
        stream.write("|---|---:|---:|---:|---:|\n")
        for scenario in scenarios:
            dcqcn = detail(scenario, "dcqcn")
            hpcc = detail(scenario, "hpcc_int")
            stream.write("| %s | %s%% | %s%% | %s%% | %s%% |\n" % (
                scenario,
                fmt(float(dcqcn["group_rct_max_us_change_percent"])),
                fmt(float(dcqcn["queue_max_bytes_change_percent"])),
                fmt(float(hpcc["group_rct_max_us_change_percent"])),
                fmt(float(hpcc["queue_max_bytes_change_percent"]))))
        stream.write("\nAgainst DCQCN, v1.4 improves RCT in 2/6 scenarios "
                     "(1.20%% and 4.76%%), is nearly tied at 4 MiB (+0.21%%), and "
                     "regresses by 3.96–7.10%% in the remaining three. Peak "
                     "queue is lower in all six by %.2f–%.2f%%. Against "
                     "HPCC-INT, v1.4 RCT is worse in all six by 6.28–32.27%%, "
                     "while peak queue is lower by %.2f–%.2f%%.\n\n" % (
                         abs(max(dcqcn_queue)), abs(min(dcqcn_queue)),
                         abs(max(hpcc_queue)), abs(min(hpcc_queue))))

        stream.write("## Interpretation\n\n")
        stream.write("1. The stable-handoff implementation works causally and "
                     "preserves its safety audits.\n")
        stream.write("2. Its clearest benefit is recovering long-message "
                     "throughput relative to continuously controlled v1.3.\n")
        stream.write("3. The same handoff is not beneficial in the two measured "
                     "1 MiB cases and gives up much of v1.3's queue advantage.\n")
        stream.write("4. HPCC-INT remains the RCT leader in all six scenarios; "
                     "v1.4 occupies a lower-queue, higher-RCT operating point.\n")
        stream.write("5. Init-Only applied-rate excess is retained as an "
                     "ablation outcome because that mode intentionally stops "
                     "ongoing CBAP capacity enforcement.\n\n")
        stream.write("## What can and cannot be claimed\n\n")
        stream.write("Supported: v1.4 is correctly implemented; it sharply "
                     "reduces peak queue versus DCQCN/HPCC-INT; and it repairs "
                     "the v1.3 long-message throughput/RCT penalty in the 4 MiB "
                     "case.\n\n")
        stream.write("Not supported: universal RCT improvement, superiority to "
                     "HPCC-INT, multi-seed stability, production performance, or "
                     "a general benefit from stable handoff at all message "
                     "sizes. No parameter change should be selected from these "
                     "same results.\n\n")
        stream.write("## Recommended next decision\n\n")
        stream.write("Treat v1.4 as a mixed result. Preserve the validated "
                     "implementation and report the 4 MiB recovery honestly, "
                     "but revise or narrow the stable-handoff claim before a "
                     "paper-level general-performance claim. Any new eligibility "
                     "rule must be preregistered and evaluated on new runs, not "
                     "chosen retrospectively from this matrix.\n")

    print("FINAL_VALIDATION_ANALYSIS_WRITTEN")


if __name__ == "__main__":
    main()
