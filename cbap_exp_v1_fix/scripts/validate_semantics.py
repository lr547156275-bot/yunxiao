#!/usr/bin/env python3
"""Validate only the preregistered CBAP-v1 semantic invariants."""
import argparse
import csv
import gzip
import json
import os
from collections import defaultdict


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CBAP = {"independent_min_grant", "cbap_init_only",
        "cbap_rate_only", "cbap_full"}


def read_csv(path):
    if os.path.isfile(path):
        return list(csv.DictReader(open(path, newline="")))
    if os.path.isfile(path + ".gz"):
        with gzip.open(path + ".gz", "rt", newline="") as stream:
            return list(csv.DictReader(stream))
    return []


def number(row, key):
    try:
        return float(row.get(key, 0))
    except (TypeError, ValueError):
        return 0.0


def write_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields,
                                extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", default=os.path.join(ROOT, "runs_semantic"))
    args = parser.parse_args()
    manifest = list(csv.DictReader(open(os.path.join(
        ROOT, "config", "semantic_manifest.csv"))))
    semantic, pacing, admission, credit, failures = [], [], [], [], []
    e2 = defaultdict(dict)
    for expected in manifest:
        run = os.path.join(args.runs, expected["scenario"],
                           expected["subcase"], expected["algorithm"],
                           "seed_" + expected["seed"])
        run_failures = []
        if not os.path.isfile(os.path.join(run, "completed.flag")):
            run_failures.append("missing_valid_run")
        algorithm = expected["algorithm"]
        flow_rows = read_csv(os.path.join(run, "cbap_flow_state.csv")) \
            if algorithm in CBAP else []
        tx_rows = read_csv(os.path.join(run, "cbap_tx_events.csv")) \
            if algorithm in CBAP else []
        if algorithm in CBAP and (not flow_rows or not tx_rows):
            run_failures.append("missing_cbap_semantic_output")
        for row in flow_rows:
            release = number(row, "network_release_ns")
            first_complete = number(row, "first_complete_fresh_feedback_ns")
            exit_ns = number(row, "admission_exit_ns")
            ordinary = int(number(row,
                                  "ordinary_rate_updates_during_admission"))
            flow_failures = []
            if ordinary != 0:
                flow_failures.append("ordinary_update_during_admission")
            if first_complete <= release:
                flow_failures.append("complete_feedback_not_post_release")
            if exit_ns < first_complete:
                flow_failures.append("admission_exit_before_complete_feedback")
            if number(row, "first_post_release_sample_ns") <= release:
                flow_failures.append("first_sample_not_post_release")
            if number(row, "pacing_violations") != 0:
                flow_failures.append("sender_pacing_violation")
            same_flow_tx = [tx for tx in tx_rows
                            if tx.get("flow_id") == row.get("flow_id")]
            admission_tx = [tx for tx in same_flow_tx
                            if tx.get("event") == "TX_SEND" and
                            int(number(tx, "phase")) == 2]
            tracking_tx = [tx for tx in same_flow_tx
                           if tx.get("event") == "TX_SEND" and
                           int(number(tx, "phase")) in (3, 4)]
            if number(row, "bytes_sent_before_fresh_feedback") > 0 and \
                    not admission_tx:
                flow_failures.append("missing_actual_admission_tx")
            if int(number(row,
                          "emergency_rate_updates_during_admission")) == 0:
                initial = number(row, "initial_admit_rate_bps")
                if any(abs(number(tx, "current_rate_bps") - initial) > 1
                       for tx in admission_tx):
                    flow_failures.append("admission_tx_not_at_initial_grant")
            credit_disabled = all(int(number(tx,
                                             "credit_gate_active")) == 0
                                  for tx in tracking_tx)
            if algorithm == "cbap_full":
                if number(row, "credit_gate_active_at_finish") != 0:
                    flow_failures.append("credit_gate_active_at_finish")
                if not credit_disabled:
                    flow_failures.append("credit_gate_active_in_tracking")
                if exit_ns > 0 and (number(row, "credit_gate_exit_ns") !=
                                    exit_ns):
                    flow_failures.append("credit_gate_exit_not_admission_exit")
            item = {
                "run_id": expected["run_id"], "algorithm": algorithm,
                "scenario": expected["scenario"], "flow_id": row["flow_id"],
                "network_release_ns": release,
                "first_post_release_sample_ns": number(
                    row, "first_post_release_sample_ns"),
                "first_complete_fresh_feedback_ns": first_complete,
                "admission_exit_ns": exit_ns,
                "ordinary_updates_during_admission": ordinary,
                "emergency_updates_during_admission": int(number(
                    row, "emergency_rate_updates_during_admission")),
                "pacing_violations": int(number(row, "pacing_violations")),
                "valid": int(not flow_failures),
                "reason": ";".join(flow_failures),
            }
            semantic.append(item)
            failures.extend("%s flow=%s %s" %
                            (expected["run_id"], row["flow_id"], reason)
                            for reason in flow_failures)
            credit.append({
                "run_id": expected["run_id"], "flow_id": row["flow_id"],
                "algorithm": algorithm,
                "credit_gate_enter_ns": number(row, "credit_gate_enter_ns"),
                "credit_gate_exit_ns": number(row, "credit_gate_exit_ns"),
                "credit_remaining_at_admission_exit": number(
                    row, "credit_remaining_at_admission_exit"),
                "tracking_actual_rate_bps": number(
                    row, "tracking_actual_rate_bps"),
                "tracking_current_rate_bps": number(
                    row, "tracking_current_rate_bps"),
                "tracking_base_rate_bps": number(row, "tracking_base_rate_bps"),
                "credit_gate_disabled_in_tracking": int(credit_disabled),
            })
        tx_by_flow = defaultdict(list)
        for row in tx_rows:
            if row.get("event") == "TX_SEND":
                tx_by_flow[row.get("flow_id", "")].append(row)
        for flow_id, rows in tx_by_flow.items():
            direct = sum(1 for row in rows
                         if number(row, "previous_tx_time_ns") > 0 and
                         number(row, "actual_gap_ns") + 1 <
                         number(row, "expected_gap_ns"))
            pacing.append({"run_id": expected["run_id"],
                           "algorithm": algorithm, "flow_id": flow_id,
                           "tx_send_rows": len(rows),
                           "direct_gap_violations": direct,
                           "valid": int(direct == 0)})
            if direct:
                failures.append("%s flow=%s direct_pacing_violation" %
                                (expected["run_id"], flow_id))
        if expected["scenario"] == "e2_batch_incast" and algorithm in CBAP:
            meta = json.load(open(os.path.join(run, "scenario_meta.json")))
            ids = set(str(value) for value in meta["new_flow_ids"])
            selected = [row for row in flow_rows if row["flow_id"] in ids]
            actual_sum = sum(number(row, "actual_admission_mean_rate_bps")
                             for row in selected)
            planned_sum = sum(number(row, "initial_admit_rate_bps")
                              for row in selected)
            e2[algorithm] = {"actual": actual_sum, "planned": planned_sum}
            admission.append({"algorithm": algorithm,
                              "actual_admission_aggregate_bps": actual_sum,
                              "planned_admission_aggregate_bps": planned_sum,
                              "actual_over_planned": actual_sum / planned_sum
                              if planned_sum else 0})
        if expected["scenario"] == "e4_parking_lot" and \
                expected["subcase"] == "staggered" and \
                algorithm == "cbap_full":
            f0 = next((row for row in flow_rows if row["flow_id"] == "2"), {})
            base = number(f0, "tracking_base_rate_bps")
            current = number(f0, "tracking_current_rate_bps")
            actual = number(f0, "tracking_actual_rate_bps")
            if current > base * 1.2 and actual <= base * 1.2:
                failures.append("e4_staggered_tracking_still_base_limited")
        failures.extend(expected["run_id"] + " " + reason
                        for reason in run_failures)

    independent = e2.get("independent_min_grant", {})
    batch = e2.get("cbap_rate_only", {})
    if not independent or not batch:
        failures.append("missing_e2_independent_or_batch")
    else:
        if independent["actual"] <= batch["actual"] * 1.05:
            failures.append("e2_independent_actual_rate_not_distinct")
        if independent["actual"] <= batch["planned"] * 1.05:
            failures.append("e2_independent_no_actual_oversubscription")
        for algorithm in ("cbap_init_only", "cbap_rate_only", "cbap_full"):
            data = e2.get(algorithm, {})
            if not data or data["actual"] > data["planned"] * 1.05:
                failures.append("e2_%s_actual_batch_capacity_violation" %
                                algorithm)

    processed = os.path.join(ROOT, "processed")
    write_csv(os.path.join(processed, "semantic_validation.csv"), semantic,
              ["run_id", "algorithm", "scenario", "flow_id",
               "network_release_ns", "first_post_release_sample_ns",
               "first_complete_fresh_feedback_ns", "admission_exit_ns",
               "ordinary_updates_during_admission",
               "emergency_updates_during_admission", "pacing_violations",
               "valid", "reason"])
    write_csv(os.path.join(processed, "pacing_audit.csv"), pacing,
              ["run_id", "algorithm", "flow_id", "tx_send_rows",
               "direct_gap_violations", "valid"])
    write_csv(os.path.join(processed, "admission_audit.csv"), admission,
              ["algorithm", "actual_admission_aggregate_bps",
               "planned_admission_aggregate_bps", "actual_over_planned"])
    write_csv(os.path.join(processed, "credit_scope_audit.csv"), credit,
              ["run_id", "flow_id", "algorithm", "credit_gate_enter_ns",
               "credit_gate_exit_ns", "credit_remaining_at_admission_exit",
               "tracking_actual_rate_bps", "tracking_current_rate_bps",
               "tracking_base_rate_bps", "credit_gate_disabled_in_tracking"])
    verdict = "SEMANTIC_PASS" if not failures else "SEMANTIC_FAIL"
    report = [verdict, "", "# CBAP-v1 semantic validation", "",
              "- Expected runs: 20", "- Located manifest entries: %d" %
              len(manifest), "- Hard-condition failures: %d" % len(failures),
              "", "## Failures", ""]
    report.extend("- " + failure for failure in failures)
    if not failures:
        report.append("- None")
    report.extend(["", "No performance or research-direction conclusion is "
                   "produced by this semantic gate."])
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    with open(os.path.join(ROOT, "reports",
                           "semantic_validation_report.md"), "w") as stream:
        stream.write("\n".join(report) + "\n")
    print(verdict)
    raise SystemExit(0 if verdict == "SEMANTIC_PASS" else 1)


if __name__ == "__main__":
    main()
