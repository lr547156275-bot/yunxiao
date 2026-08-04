#!/usr/bin/env python3
"""Validate the fixed nine-run event-level PFC semantic audit."""
import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT.parents[1]
PREFLIGHT = ROOT.parent / "final_preflight"
MANIFEST = PREFLIGHT / "pfc_audit_manifest.csv"
EXPECTED = [
    ("msg_4m_n16_g50", "open_loop_pfc_configured"),
    ("msg_4m_n16_g50", "open_loop_pfc_disabled"),
    ("msg_64k_n16_g50", "open_loop_pfc_configured"),
    ("msg_64k_n16_g50", "open_loop_pfc_disabled"),
    ("msg_64k_n16_g50", "dcqcn"),
    ("msg_64k_n16_g50", "hpcc_int"),
    ("msg_64k_n16_g50", "bop_qb"),
    ("n64_64k_g50", "open_loop_pfc_configured"),
    ("n64_64k_g50", "open_loop_pfc_disabled"),
]
MODES = {"open_loop_pfc_configured": 0, "open_loop_pfc_disabled": 0,
         "dcqcn": 1, "hpcc_int": 3, "bop_qb": 15}
EVENTS = ("pause_generated", "pause_received", "sender_paused",
          "resume_generated", "resume_received", "sender_resumed")
SUMMARY_COUNTER = {
    "pause_generated": "pause_generated_count",
    "pause_received": "pause_received_count",
    "sender_paused": "sender_paused_count",
    "resume_generated": "resume_generated_count",
    "resume_received": "resume_received_count",
    "sender_resumed": "sender_resumed_count",
}
INPUT_COLUMNS = {
    "topology.txt": "topology_sha256", "flow.txt": "flow_sha256",
    "rounds.txt": "rounds_sha256", "fixed_paths.txt": "fixed_paths_sha256",
    "trace.txt": "trace_sha256",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def config(path):
    result = {}
    for line in path.read_text().splitlines():
        parts = line.split()
        if parts and not parts[0].startswith("#"):
            result[parts[0]] = " ".join(parts[1:])
    return result


def manifest_rows():
    with open(MANIFEST, newline="") as stream:
        return list(csv.DictReader(stream))


def static_sender_gate_errors():
    errors = []
    device = (SIM / "src/point-to-point/model/qbb-net-device.cc").read_text()
    required = (
        "GetNextQindex(m_paused)",
        "!paused[qp->m_pg]",
        "m_queue->DequeueRR(m_paused)",
        "m_paused[qIndex] = true",
        "m_paused[qIndex] = false",
    )
    for token in required:
        if token not in device:
            errors.append("sender_gate_missing_" +
                          token.replace(" ", "_").replace("(", "_").
                          replace(")", "").replace("->", "_"))
    return errors


def topology_peer_ports(path):
    """Map (node, ifIndex) to the peer endpoint using topology link order."""
    lines = [line.split() for line in path.read_text().splitlines()
             if line.strip()]
    link_count = int(lines[0][2])
    counters = collections.Counter()
    peers = {}
    for fields in lines[2:2 + link_count]:
        left, right = int(fields[0]), int(fields[1])
        counters[left] += 1
        counters[right] += 1
        left_key = (left, counters[left])
        right_key = (right, counters[right])
        peers[left_key] = right_key
        peers[right_key] = left_key
    return peers


def validate_link_delivery(rows, peers):
    errors = []
    for generated, received in (
            ("pause_generated", "pause_received"),
            ("resume_generated", "resume_received")):
        candidates = [row for row in rows if row["event_type"] == received]
        used = set()
        for source in (row for row in rows
                       if row["event_type"] == generated):
            endpoint = (int(source["node_id"]), int(source["port_id"]))
            peer = peers.get(endpoint)
            if peer is None:
                errors.append(generated + "_unknown_port")
                continue
            match = None
            for index, target in enumerate(candidates):
                if index in used:
                    continue
                if (int(target["node_id"]), int(target["device_id"])) == peer \
                        and target["priority_or_pg"] == \
                        source["priority_or_pg"] and \
                        int(target["timestamp_ns"]) >= \
                        int(source["timestamp_ns"]):
                    match = index
                    break
            if match is None:
                errors.append(generated + "_not_delivered_to_peer_port")
            else:
                used.add(match)

    # A received control frame must immediately cause the matching device/PG
    # state transition (the callbacks may share the same ns timestamp).
    for received, transition in (
            ("pause_received", "sender_paused"),
            ("resume_received", "sender_resumed")):
        candidates = [row for row in rows if row["event_type"] == transition]
        used = set()
        for source in (row for row in rows
                       if row["event_type"] == received):
            match = None
            for index, target in enumerate(candidates):
                if index in used:
                    continue
                if target["node_id"] == source["node_id"] and \
                        target["device_id"] == source["device_id"] and \
                        target["priority_or_pg"] == source["priority_or_pg"] \
                        and int(target["timestamp_ns"]) >= \
                        int(source["timestamp_ns"]):
                    match = index
                    break
            if match is None:
                errors.append(received + "_without_device_transition")
            else:
                used.add(match)
    return errors


def validate_event_chain(rows, summary, topology_path):
    errors = []
    counts = collections.Counter(row["event_type"] for row in rows)
    for event, field in SUMMARY_COUNTER.items():
        try:
            if counts[event] != int(summary[field]):
                errors.append("counter_mismatch_" + event)
        except (KeyError, TypeError, ValueError):
            errors.append("summary_" + field)

    # The trace is append-only; event time must never run backwards.
    timestamps = [int(row["timestamp_ns"]) for row in rows]
    if timestamps != sorted(timestamps):
        errors.append("event_time_order")

    # Prefix relationships ensure that reception/state changes cannot appear
    # without their causal predecessor. Multiple ports may interleave.
    prefix = collections.Counter()
    for row in rows:
        prefix[row["event_type"]] += 1
        if prefix["pause_received"] > prefix["pause_generated"]:
            errors.append("pause_received_without_generated")
        if prefix["sender_paused"] > prefix["pause_received"]:
            errors.append("sender_paused_without_received")
        if prefix["resume_received"] > prefix["resume_generated"]:
            errors.append("resume_received_without_generated")
        if prefix["sender_resumed"] > prefix["resume_received"]:
            errors.append("sender_resumed_without_received")

    generated = counts["pause_generated"]
    if generated:
        if any(counts[event] == 0 for event in EVENTS):
            errors.append("partial_six_event_chain")
        if counts["pause_generated"] != counts["resume_generated"]:
            errors.append("switch_pause_resume_imbalance")
        if counts["pause_received"] != counts["sender_paused"]:
            errors.append("sender_pause_transition_imbalance")
        if counts["resume_received"] != counts["sender_resumed"]:
            errors.append("sender_resume_transition_imbalance")
        errors.extend(validate_link_delivery(
            rows, topology_peer_ports(topology_path)))
    return errors


def validate_one(run):
    errors = static_sender_gate_errors()
    required = ["run_meta.json", "config.txt", "topology.txt",
                "pfc_event_trace.csv",
                "pfc_semantic_summary.json", "round_summary.csv",
                "flow_summary.csv", "group_round_summary.csv"]
    for name in required:
        if not (run / name).exists():
            errors.append("missing_" + name)
    if errors:
        return sorted(set(errors))

    meta = json.load(open(run / "run_meta.json"))
    cfg = config(run / "config.txt")
    algorithm = meta.get("algorithm", "")
    if meta.get("exit_status") != 0:
        errors.append("exit_status")
    if meta.get("log_truncated"):
        errors.append("log_truncated")
    if algorithm not in MODES or int(cfg.get("CC_MODE", -1)) != \
            MODES.get(algorithm):
        errors.append("cc_mode")
    expected_runtime = algorithm != "open_loop_pfc_disabled"
    if bool(int(cfg.get("PFC_RUNTIME_ENABLE", -1))) != expected_runtime:
        errors.append("pfc_runtime_config")
    if cfg.get("PFC_SEMANTIC_AUDIT_ENABLE") != "1":
        errors.append("pfc_audit_not_enabled")

    summary = json.load(open(run / "pfc_semantic_summary.json"))
    summary_fields = (
        "queue_object_id", "pfc_queue_object_id", "queue_priority",
        "pfc_priority", "pfc_threshold_bytes", "queue_max_bytes",
        "pause_generated_count", "pause_received_count",
        "sender_paused_count", "resume_generated_count",
        "resume_received_count", "sender_resumed_count",
        "pause_duration_us", "pfc_runtime_enabled",
        "queue_and_pfc_objects_identical", "pfc_path_verified",
    )
    for field in summary_fields:
        if field not in summary:
            errors.append("summary_" + field)
    if errors:
        return sorted(set(errors))
    if not str(summary["queue_object_id"]).startswith("BEgressQueue@"):
        errors.append("queue_object_type")
    if not str(summary["pfc_queue_object_id"]).startswith("SwitchMmu@"):
        errors.append("pfc_object_type")
    if summary["queue_and_pfc_objects_identical"]:
        errors.append("queue_pfc_role_conflation")
    if int(summary["queue_priority"]) != int(summary["pfc_priority"]) or \
            int(summary["pfc_priority"]) != int(cfg["PFC_AUDIT_PRIORITY"]):
        errors.append("priority_pg_mismatch")
    if int(summary["pfc_threshold_bytes"]) <= 0:
        errors.append("pfc_threshold_nonpositive")
    if bool(summary["pfc_runtime_enabled"]) != expected_runtime:
        errors.append("pfc_runtime_summary")

    with open(run / "pfc_event_trace.csv", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        required_event_fields = {
            "timestamp_ns", "node_id", "device_id", "port_id",
            "priority_or_pg", "queue_bytes", "pfc_threshold_bytes",
            "event_type", "pause_quanta", "pause_duration_ns",
            "sender_paused", "packet_owner",
        }
        if not reader.fieldnames or not required_event_fields.issubset(
                reader.fieldnames):
            errors.append("event_schema")

    for row in rows:
        if row.get("event_type") not in EVENTS:
            errors.append("event_type")
            continue
        if row.get("packet_owner") != "pfc_control":
            errors.append("event_owner")
        for key in ("timestamp_ns", "node_id", "device_id", "port_id",
                    "priority_or_pg", "queue_bytes",
                    "pfc_threshold_bytes", "pause_quanta",
                    "pause_duration_ns", "sender_paused"):
            try:
                value = float(row[key])
                if not math.isfinite(value) or value < 0:
                    errors.append("invalid_" + key)
            except (KeyError, TypeError, ValueError):
                errors.append("invalid_" + key)
        if row.get("event_type") == "pause_generated" and \
                float(row["queue_bytes"]) < float(row["pfc_threshold_bytes"]):
            errors.append("pause_below_event_threshold")
        if row.get("event_type") == "sender_paused" and \
                row.get("sender_paused") != "1":
            errors.append("sender_pause_state")
        if row.get("event_type") == "sender_resumed" and \
                row.get("sender_paused") != "0":
            errors.append("sender_resume_state")

    errors.extend(validate_event_chain(rows, summary, run / "topology.txt"))
    event_total = sum(int(summary[SUMMARY_COUNTER[event]])
                      for event in EVENTS)
    if not expected_runtime and event_total:
        errors.append("disabled_mode_has_pfc_events")
    if bool(summary["pfc_path_verified"]) != (
            all(int(summary[SUMMARY_COUNTER[event]]) > 0 for event in EVENTS)):
        errors.append("pfc_path_verified_semantics")

    rounds = list(csv.DictReader(open(run / "round_summary.csv")))
    if not rounds or any(r.get("ack_completion_time", "") in ("", "0")
                         for r in rounds):
        errors.append("barrier_or_round_incomplete")
    flows = list(csv.DictReader(open(run / "flow_summary.csv")))
    if not flows or any(r.get("completed", "").lower() not in ("1", "true")
                        for r in flows):
        errors.append("flow_incomplete")
    return sorted(set(errors))


def validate_static():
    errors = static_sender_gate_errors()
    rows = manifest_rows()
    pairs = [(r["scenario"], r["algorithm"]) for r in rows]
    if pairs != EXPECTED or len(set(pairs)) != 9:
        errors.append("manifest_matrix")
    for row in rows:
        if row["seed"] != "1" or int(row["cc_mode"]) != \
                MODES[row["algorithm"]]:
            errors.append("manifest_mode_or_seed")
        source = SIM / row["source_run"]
        for name, column in INPUT_COLUMNS.items():
            if not (source / name).exists() or digest(source / name) != \
                    row[column]:
                errors.append("manifest_hash_" + name)
        if digest(source / "config.txt") != row["source_config_sha256"]:
            errors.append("manifest_source_config_hash")
    source = (SIM / "scratch/third.cc").read_text()
    for event in EVENTS:
        if '"' + event + '"' not in source:
            errors.append("source_missing_event_" + event)
    return sorted(set(errors))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", default=str(ROOT / "audit_runs"))
    parser.add_argument("--static", action="store_true")
    parser.add_argument("--run")
    args = parser.parse_args()
    if args.static:
        errors = validate_static()
        if errors:
            print("FAIL", "|".join(errors))
            return 1
        print("PASS PFC contract matrix=9 sender_stop_gate=verified")
        return 0
    if args.run:
        errors = validate_one(Path(args.run))
        if errors:
            print("FAIL", "|".join(errors))
            return 1
        print("PASS", args.run)
        return 0
    failures = []
    runs = Path(args.runs)
    for scenario, algorithm in EXPECTED:
        run = runs / scenario / algorithm / "seed_1"
        errors = validate_one(run)
        if errors:
            failures.append((scenario, algorithm, "|".join(errors)))

    # Configured/disabled inputs must match except explicit diagnostic fields.
    for scenario in ("msg_4m_n16_g50", "msg_64k_n16_g50",
                     "n64_64k_g50"):
        a = runs / scenario / "open_loop_pfc_configured" / "seed_1"
        b = runs / scenario / "open_loop_pfc_disabled" / "seed_1"
        if a.exists() and b.exists():
            ca, cb = config(a / "config.txt"), config(b / "config.txt")
            for key in set(ca) | set(cb):
                if key in {"PFC_RUNTIME_ENABLE", "ALGORITHM"}:
                    continue
                if ca.get(key) != cb.get(key):
                    failures.append((scenario, "open_loop_pair",
                                     "config_diff_" + key))
    for scenario in {scenario for scenario, _ in EXPECTED}:
        members = [runs / scenario / algorithm / "seed_1"
                   for candidate, algorithm in EXPECTED
                   if candidate == scenario]
        existing = [run for run in members if (run / "run_meta.json").exists()]
        if len(existing) > 1:
            reference = json.load(open(existing[0] / "run_meta.json"))
            for run in existing[1:]:
                meta = json.load(open(run / "run_meta.json"))
                for name in INPUT_COLUMNS:
                    if meta["input_hashes"].get(name) != \
                            reference["input_hashes"].get(name):
                        failures.append((scenario, run.parent.name,
                                         "input_hash_" + name))
    if failures:
        for failure in failures:
            print("FAIL", *failure)
        return 1
    print("PASS semantic audit runs=9")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
