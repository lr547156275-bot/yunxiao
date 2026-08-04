#!/usr/bin/env python3
import csv
import json
import os
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RUNS = os.path.join(ROOT, "runs_semantic")
PROCESSED = os.path.join(ROOT, "processed")
REPORT = os.path.join(ROOT, "reports", "handoff_semantic_report.md")


def read_csv(path):
    return list(csv.DictReader(open(path, newline=""))) if os.path.isfile(path) else []


def truth(value):
    return str(value).lower() in ("1", "true", "yes")


def load_runs():
    result = []
    for base, _, files in os.walk(RUNS):
        if "run_meta.json" in files:
            result.append((base, json.load(open(os.path.join(base, "run_meta.json")))))
    return sorted(result)


def main():
    os.makedirs(PROCESSED, exist_ok=True)
    runs = load_runs()
    failures, audit, packet, owners, messages = [], [], [], [], []
    if len(runs) != 7:
        failures.append("expected 7 runs, found %d" % len(runs))
    for d, meta in runs:
        tag = "%s/%s" % (meta.get("scenario"), meta.get("algorithm_name"))
        if not os.path.isfile(os.path.join(d, "completed.flag")):
            failures.append("%s missing completed.flag" % tag)
        checked = subprocess.run(
            ["python3", os.path.join(ROOT, "scripts", "check_outputs.py"), d],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if checked.returncode:
            failures.append("%s output check: %s" %
                            (tag, checked.stdout.strip()))
        if meta.get("exit_status") != 0:
            failures.append("%s exit_status=%r" % (tag, meta.get("exit_status")))
        batches = read_csv(os.path.join(d, "cbap_handoff_summary.csv"))
        flows = read_csv(os.path.join(d, "cbap_handoff_flow.csv"))
        ownership = read_csv(os.path.join(d, "controller_ownership.csv"))
        applied = read_csv(os.path.join(d, "applied_rate_audit.csv"))
        flow_state = read_csv(os.path.join(d, "cbap_flow_state.csv"))
        expected = meta.get("expected_handoff", "measure")
        occurred = [r for r in batches if truth(r.get("handoff_occurred"))]
        if expected in ("required", "required_remaining") and not occurred:
            failures.append("%s required handoff missing" % tag)
        if expected in ("forbidden", "shadow_only") and occurred:
            failures.append("%s forbidden handoff occurred" % tag)
        if expected == "required_remaining" and occurred and not any(
                int(float(r["remaining_bytes_total"])) > 0 for r in occurred):
            failures.append("%s handoff has no remaining bytes" % tag)
        if expected == "shadow_only" and (not batches or not any(
                int(float(r.get("shadow_handoff_candidate_time", 0))) > 0
                for r in batches)):
            failures.append("%s missing v1.3 shadow candidate" % tag)
        if expected == "after_recovery":
            recovery_epochs = int(meta.get(
                "diagnostic_recovery_until_epoch", 0))
            control_epoch = int(meta.get("control_epoch_ns", 0))
            if not batches or recovery_epochs <= 0 or control_epoch <= 0:
                failures.append("%s invalid recovery diagnostic metadata" % tag)
            for row in occurred:
                earliest = (int(row["tracking_enter_ns"]) +
                            recovery_epochs * control_epoch)
                if int(row["handoff_execute_ns"]) < earliest:
                    failures.append("%s handoff occurred during forced recovery" %
                                    tag)
            if not occurred and batches and not all(
                    r.get("no_handoff_reason") == "completed_before_handoff"
                    for r in batches):
                failures.append("%s recovery diagnostic ended without a "
                                "causal terminal reason" % tag)
        for r in batches:
            ok = True; reasons = []
            if truth(r.get("handoff_occurred")):
                checks = [
                    (int(r["stable_epoch_count"]) >= 2, "stable_epochs"),
                    (int(r["handoff_execute_ns"]) >= int(r["tracking_enter_ns"]) +
                     int(r["minimum_tracking_time_ns"]), "minimum_tracking"),
                    (int(r["grants_after_handoff"]) == 0, "post_grants"),
                    (int(r["applied_rate_sum_before"]) ==
                     int(r["dcqcn_rate_sum_after_init"]), "rate_sum_init"),
                    (int(r["max_per_flow_rate_jump_bps"]) <= 1, "rate_jump"),
                ]
                for passed, name in checks:
                    if not passed: ok = False; reasons.append(name)
            audit.append(dict(run=tag, batch_id=r.get("batch_id"),
                              handoff_occurred=r.get("handoff_occurred"),
                              passed=int(ok), reason=";".join(reasons)))
            if not ok: failures.append("%s batch %s: %s" %
                                       (tag, r.get("batch_id"), reasons))
        for r in flows:
            ok = (int(r["phase_before"]) == 3 and int(r["phase_after"]) == 7 and
                  int(r["cbap_applied_rate_before"]) ==
                  int(r["dcqcn_current_rate_after"]) ==
                  int(r["dcqcn_target_rate_after"]) and
                  int(r["next_tx_after"]) >= int(r["next_tx_before"]) and
                  not truth(r["catchup_burst_detected"]))
            packet.append(dict(run=tag, flow_id=r["flow_id"], passed=int(ok),
                               packet_gap_required=r["packet_gap_required"],
                               packet_gap_actual=r["packet_gap_actual"]))
            if not ok: failures.append("%s flow %s handoff packet audit" %
                                       (tag, r["flow_id"]))
        for r in ownership:
            dual = truth(r["cbap_rate_update"]) and truth(r["dcqcn_rate_update"])
            bad = r["owner"] == "CBAP" and int(r["phase"]) == 7
            owners.append(dict(run=tag, **r, passed=int(not dual and not bad)))
            if dual or bad: failures.append("%s dual/late ownership update" % tag)
        for r in applied:
            if truth(r.get("applied_capacity_violation")):
                failures.append("%s applied capacity violation" % tag)
        for r in flow_state:
            if int(float(r.get("capacity_violations", 0))) != 0:
                failures.append("%s flow %s capacity violation" %
                                (tag, r.get("flow_id")))
            if int(float(r.get("credit_violations", 0))) != 0:
                failures.append("%s flow %s credit violation" %
                                (tag, r.get("flow_id")))
            if int(float(r.get("pacing_violations", 0))) != 0:
                failures.append("%s flow %s pacing violation" %
                                (tag, r.get("flow_id")))
        for r in read_csv(os.path.join(d, "control_message_audit.csv")):
            messages.append(dict(run=tag, **r))

    def write(name, rows, fields):
        with open(os.path.join(PROCESSED, name), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader(); w.writerows(rows)
    write("handoff_audit.csv", audit,
          ["run", "batch_id", "handoff_occurred", "passed", "reason"])
    write("handoff_packet_audit.csv", packet,
          ["run", "flow_id", "passed", "packet_gap_required",
           "packet_gap_actual"])
    write("controller_ownership_audit.csv", owners,
          ["run", "time_ns", "epoch", "batch_id", "flow_id", "phase",
           "owner", "cbap_rate_update", "dcqcn_rate_update", "passed"])
    write("control_message_audit.csv", messages,
          ["run", "time_ns", "epoch", "batch_id",
           "cbap_active_control_message_count",
           "cbap_monitoring_only_message_count", "grant_message_count"])
    status = "HANDOFF_SEMANTIC_PASS" if not failures else "HANDOFF_SEMANTIC_FAIL"
    with open(REPORT, "w") as f:
        f.write(status + "\n\n# Stable-handoff semantic report\n\n")
        f.write("Reused runs: %d/7. This report is a correctness audit, not a "
                "performance conclusion.\n\n" % len(runs))
        f.write("## Failures\n\n")
        f.write("None.\n" if not failures else
                "\n".join("- " + x for x in failures) + "\n")
    print(status)


if __name__ == "__main__":
    main()
