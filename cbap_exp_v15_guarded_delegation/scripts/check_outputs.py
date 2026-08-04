#!/usr/bin/env python3
import argparse
import csv
import json
import math
import os


def rows(path):
    if not os.path.isfile(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("run_dir")
    p.add_argument("--allow-no-complete-flag", action="store_true")
    a = p.parse_args()
    d = os.path.abspath(a.run_dir)
    required = ["run_meta.json", "manifest.json", "scenario_meta.json",
                "flow_summary.csv", "round_summary.csv",
                "group_round_summary.csv"]
    errors = ["missing %s" % x for x in required
              if not os.path.isfile(os.path.join(d, x))]
    if not a.allow_no_complete_flag and not os.path.isfile(
            os.path.join(d, "completed.flag")):
        errors.append("missing completed.flag")
    if errors:
        raise SystemExit("; ".join(errors))
    meta = json.load(open(os.path.join(d, "run_meta.json")))
    scenario = json.load(open(os.path.join(d, "scenario_meta.json")))
    if meta.get("exit_status") != 0:
        errors.append("exit_status != 0")
    if meta.get("log_truncated"):
        errors.append("log truncated")
    flow = rows(os.path.join(d, "flow_summary.csv"))
    rounds = rows(os.path.join(d, "round_summary.csv"))
    if not flow or not rounds:
        errors.append("empty flow or round summary")
    pending = set(int(x) for x in scenario.get("pending_flow_ids", []))
    incumbents = set(int(x) for x in scenario.get("incumbent_flow_ids", []))
    if not pending:
        errors.append("scenario has no registered pending_flow_ids")
    if pending & incumbents:
        errors.append("pending and incumbent flow sets overlap")
    if scenario.get("pending_count") is not None and \
            int(scenario["pending_count"]) != len(pending):
        errors.append("pending_count does not match pending_flow_ids")
    flow_by_id = {int(r["flow_id"]): r for r in flow}
    missing_pending_flows = sorted(pending - set(flow_by_id))
    if missing_pending_flows:
        errors.append("missing completed pending flows: %s" %
                      missing_pending_flows)
    incomplete_pending_flows = sorted(
        fid for fid in pending & set(flow_by_id)
        if str(flow_by_id[fid].get("completed", "0")).lower() not in
        ("1", "true", "yes"))
    if incomplete_pending_flows:
        errors.append("incomplete pending flows: %s" %
                      incomplete_pending_flows)
    pending_rounds = [r for r in rounds if int(r["flow_id"]) in pending]
    round_flow_ids = set(int(r["flow_id"]) for r in pending_rounds)
    missing_pending_rounds = sorted(pending - round_flow_ids)
    if missing_pending_rounds:
        errors.append("missing pending rounds: %s" % missing_pending_rounds)
    incomplete_pending_rounds = sorted(set(
        int(r["flow_id"]) for r in pending_rounds
        if float(r.get("ack_completion_time", 0) or 0) <= 0))
    if incomplete_pending_rounds:
        errors.append("pending rounds not ACK-completed: %s" %
                      incomplete_pending_rounds)
    # Incumbents are preregistered long-lived background workloads. They must
    # exist in the schedule, but are deliberately not required to finish by
    # the collective-oriented simulation stop time.
    round_ids = set(int(r["flow_id"]) for r in rounds)
    missing_incumbent_rounds = sorted(incumbents - round_ids)
    if missing_incumbent_rounds:
        errors.append("missing incumbent workload rounds: %s" %
                      missing_incumbent_rounds)
    for table, name in ((flow, "flow"), (rounds, "round")):
        for i, row in enumerate(table):
            text = " ".join(row.values()).lower()
            if "nan" in text or "inf" in text:
                errors.append("%s row %d non-finite" % (name, i))
    flow_state = rows(os.path.join(d, "cbap_flow_state.csv"))
    for field in ("capacity_violations", "credit_violations",
                  "pacing_violations"):
        violating = sorted(set(
            int(r.get("flow_id", -1)) for r in flow_state
            if int(float(r.get(field, 0) or 0)) != 0))
        if violating:
            errors.append("%s in flows: %s" % (field, violating))
    applied = rows(os.path.join(d, "applied_rate_audit.csv"))
    # INIT_ONLY deliberately returns ongoing control to DCQCN after admission;
    # its later aggregate applied-rate excess is a measured ablation outcome,
    # not a violation of a capacity-enforcement promise. RATE_ONLY and the
    # FULL modes do make that promise.
    enforces_applied_capacity = int(meta["cc_mode"]) in (22, 23, 24, 25, 26, 27)
    if enforces_applied_capacity and any(
            str(r.get("applied_capacity_violation", "0")).lower() in
            ("1", "true", "yes") for r in applied):
        errors.append("applied capacity violation")
    if int(meta["cc_mode"]) in (25, 26, 27):
        for name in ("cbap_handoff_summary.csv", "control_message_audit.csv"):
            if not os.path.isfile(os.path.join(d, name)):
                errors.append("missing %s" % name)
    if int(meta["cc_mode"]) == 26:
        for name in ("cbap_handoff_flow.csv", "controller_ownership.csv",
                     "applied_rate_audit.csv", "sender_tx_trace.csv"):
            if not os.path.isfile(os.path.join(d, name)):
                errors.append("missing %s" % name)
    if int(meta["cc_mode"]) == 27:
        for name in ("controller_ownership.csv", "applied_rate_audit.csv",
                     "sender_tx_trace.csv", "envelope_link_audit.csv",
                     "envelope_flow_audit.csv", "incumbent_progress.csv"):
            if not os.path.isfile(os.path.join(d, name)):
                errors.append("missing %s" % name)
        envelope = rows(os.path.join(d, "envelope_link_audit.csv"))
        if any(str(r.get("envelope_capacity_violation", "0")).lower()
               in ("1", "true", "yes") for r in envelope):
            errors.append("envelope capacity violation")
        owners = rows(os.path.join(d, "envelope_flow_audit.csv"))
        if any(r.get("desired_writer") != "DCQCN" or
               r.get("applied_writer") != "ENVELOPE_PROJECTOR"
               for r in owners):
            errors.append("controller ownership conflict")
    if errors:
        raise SystemExit("; ".join(errors))
    print("PASS %s" % d)


if __name__ == "__main__":
    main()
