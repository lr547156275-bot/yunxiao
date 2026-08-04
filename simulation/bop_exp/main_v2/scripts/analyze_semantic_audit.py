#!/usr/bin/env python3
"""Summarize PFC semantics without converting absent data to zero."""
import csv
import json
from pathlib import Path
from check_semantic_audit import (
    EVENTS, EXPECTED, SUMMARY_COUNTER, static_sender_gate_errors, validate_one)

ROOT = Path(__file__).resolve().parents[1]


def main():
    runs = ROOT / "audit_runs"
    output = ROOT / "analysis/pfc_semantic_audit.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "scenario", "algorithm", "seed", "audit_status",
        "queue_object_id", "pfc_queue_object_id",
        "queue_and_pfc_objects_identical", "queue_priority", "pfc_priority",
        "queue_max_bytes", "pfc_threshold_bytes",
        "pause_generated_count", "pause_received_count",
        "sender_paused_count", "resume_generated_count",
        "resume_received_count", "sender_resumed_count",
        "pause_duration_us", "pfc_runtime_enabled", "pfc_path_verified",
        "sender_stop_static_gate_verified", "classification",
        "invalid_reason",
    ]
    gate = not static_sender_gate_errors()
    rows = []
    for scenario, algorithm in EXPECTED:
        run = runs / scenario / algorithm / "seed_1"
        summary_path = run / "pfc_semantic_summary.json"
        if not summary_path.exists():
            rows.append({
                "scenario": scenario, "algorithm": algorithm, "seed": 1,
                "audit_status": "NOT_RUN",
                "sender_stop_static_gate_verified": int(gate),
                "classification": "PENDING_MANUAL_AUDIT",
                "invalid_reason": "missing_pfc_semantic_summary.json",
            })
            continue
        errors = validate_one(run)
        summary = json.load(open(summary_path))
        event_counts = [int(summary.get(SUMMARY_COUNTER[event], -1))
                        for event in EVENTS]
        if errors:
            classification = "PFC_AUDIT_INVALID"
            status = "INVALID"
        elif not summary["pfc_runtime_enabled"]:
            classification = "PFC_DISABLED_CONFIRMED"
            status = "COMPLETE"
        elif all(value > 0 for value in event_counts):
            classification = "PFC_PATH_VALID"
            status = "COMPLETE"
        else:
            classification = "PFC_NOT_TRIGGERED"
            status = "COMPLETE"
        row = {
            "scenario": scenario, "algorithm": algorithm, "seed": 1,
            "audit_status": status, "classification": classification,
            "sender_stop_static_gate_verified": int(gate),
            "invalid_reason": "|".join(errors),
        }
        for key in fields:
            if key in summary:
                row[key] = summary[key]
        rows.append(row)
    with open(output, "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(output)


if __name__ == "__main__":
    main()
