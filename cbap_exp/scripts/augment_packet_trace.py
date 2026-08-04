#!/usr/bin/env python3
"""Append exact control/event records to the bounded seed-1 DATA trace.

Packet dequeue rows are emitted in C++ at the actual switch event.  This
post-run merge adds exact timestamps already recorded by the coordinator,
round, PFC and completion instrumentation.  Rows are intentionally append-only;
consumers sort by timestamp_ns when a total order is needed.
"""
import csv
import gzip
import os
import shutil
import sys


def rows(path):
    if not os.path.isfile(path):
        return []
    with open(path, newline="") as stream:
        return list(csv.DictReader(stream))


def main(run):
    raw = os.path.join(run, "cbap_packet_trace.csv")
    compressed = raw + ".gz"
    if os.path.isfile(raw):
        source = open(raw, newline="")
        destination_path = raw + ".merged"
        destination = open(destination_path, "w", newline="")
        output_compressed = False
    elif os.path.isfile(compressed):
        source = gzip.open(compressed, "rt", newline="")
        destination_path = compressed + ".merged"
        destination = gzip.open(destination_path, "wt", newline="")
        output_compressed = True
    else:
        raise SystemExit("missing packet trace: " + run)
    reader = csv.DictReader(source)
    fields = reader.fieldnames
    writer = csv.DictWriter(destination, fieldnames=fields)
    writer.writeheader()
    for row in reader:
        writer.writerow(row)

    def event(timestamp, name, source_row=None, **values):
        row = dict((field, "") for field in fields)
        row.update({"timestamp_ns": int(float(timestamp)),
                    "event": name, "packet_type": "CONTROL"})
        if source_row:
            row.update(values)
        else:
            row.update(values)
        writer.writerow(row)

    for row in rows(os.path.join(run, "cbap_admission.csv")):
        common = {
            "batch_id": row["batch_id"], "flow_id": row["flow_id"],
            "current_rate": row["initial_rate_bps"],
            "target_rate": row["admit_rate_bps"],
            "local_grant": row["base_rate_bps"],
            "path_min_grant": row["admit_rate_bps"],
            "admit_rate": row["admit_rate_bps"],
            "base_rate": row["base_rate_bps"],
            "credit_remaining": row["credit_bytes"],
        }
        event(row["plan_start_ns"], "PLAN_START", row, **common)
        event(row["plan_complete_ns"], "PLAN_COMPLETE", row, **common)
        event(row["network_release_ns"], "BATCH_RELEASE", row, **common)
    for row in rows(os.path.join(run, "cbap_port_summary.csv")):
        common = {
            "switch": row["switch_id"], "egress_port": row["egress_port"],
            "queue_after": row["queue_bytes"],
            "port_state": row["port_state"], "root_id": row["root_id"],
        }
        event(row["delivery_time_ns"], "PORT_SUMMARY", row, **common)
        state = int(float(row["port_state"]))
        if state == 2:
            event(row["delivery_time_ns"], "ROOT_DETECTED", row, **common)
        elif state == 3:
            event(row["delivery_time_ns"], "PROPAGATED_DETECTED",
                  row, **common)
    for row in rows(os.path.join(run, "cbap_rate_transitions.csv")):
        old = int(float(row["old_rate_bps"]))
        new = int(float(row["new_rate_bps"]))
        if new > old:
            name = "RATE_INCREASE"
        elif new < old:
            name = "RATE_DECREASE"
        else:
            name = "GRANT_UPDATE"
        common = {
            "batch_id": row["batch_id"], "flow_id": row["flow_id"],
            "current_rate": row["new_rate_bps"],
            "target_rate": row["target_rate_bps"],
            "path_min_grant": row["target_rate_bps"],
            "credit_remaining": row["credit_remaining_bytes"],
            "phase": row["phase_after"], "root_id": row["root_id"],
            "feedback_age": row["feedback_age_ns"],
        }
        event(row["time_ns"], name, row, **common)
        before, after = int(row["phase_before"]), int(row["phase_after"])
        if before != 4 and after == 4:
            event(row["time_ns"], "RECOVERY_ENTER", row, **common)
        if before == 4 and after != 4:
            event(row["time_ns"], "RECOVERY_EXIT", row, **common)
    for row in rows(os.path.join(run, "pfc_events.csv")):
        name = "PFC_PAUSE" if row["event_type"] in ("1", "PAUSE",
                                                     "pause") else "PFC_RESUME"
        event(row["time_ns"], name, row, switch=row["node_id"],
              egress_port=row["if_index"])
    for row in rows(os.path.join(run, "round_summary.csv")):
        ack_ns = float(row["ack_completion_time"]) * 1e9
        event(ack_ns, "ACK_ARRIVE", row, flow_id=row["flow_id"],
              batch_id=row["round_group_id"])
    for row in rows(os.path.join(run, "cbap_flow_state.csv")):
        if int(float(row["finish_ns"])):
            event(row["finish_ns"], "FLOW_COMPLETE", row,
                  flow_id=row["flow_id"], batch_id=row["batch_id"],
                  current_rate=row["final_rate_bps"],
                  target_rate=row["final_rate_bps"], phase=5)
    source.close()
    destination.close()
    target = compressed if output_compressed else raw
    os.replace(destination_path, target)


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]))
