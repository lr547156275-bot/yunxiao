#!/usr/bin/env python3
"""Build the immutable main-v2 registry and validate main-v1 reuse candidates."""
import csv
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT.parents[1]
V1 = ROOT.parent / "main_v1"
CONFIG = ROOT / "config"

FORMAL = ("dctcp", "dcqcn", "timely", "hpcc_int", "bop_qb")
BEST_CC = ("dctcp", "dcqcn", "timely", "hpcc_int")
ABLATION = ("crfm_gate", "bop")
WIRE = ("dcqcn_wire_equalized",)
CC_MODE = {
    "open_loop_pfc_configured": 0, "open_loop_pfc_disabled": 0,
    "dctcp": 8, "dcqcn": 1, "timely": 7, "hpcc_int": 3,
    "bop_qb": 15, "crfm_gate": 12, "bop": 13,
    "dcqcn_wire_equalized": 17,
}
OUTPUT_KEYS = {
    "PFC_OUTPUT_FILE", "FCT_OUTPUT_FILE", "FLOW_SUMMARY_FILE",
    "ROUND_SUMMARY_FILE", "FEEDBACK_SUMMARY_FILE",
    "CONTROLLER_SUMMARY_FILE", "GROUP_ROUND_SUMMARY_FILE",
    "FLOW_PLAN_FILE", "LINK_TIMESERIES_FILE",
    "SELECTED_FLOW_TIMESERIES_FILE", "WIRE_SIZE_SUMMARY_FILE",
    "RELEASE_QUEUE_SUMMARY_FILE", "BOP_QB_GROUP_DECISIONS_FILE",
}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path):
    with open(path, newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def parse_config(path):
    values = {}
    with open(path) as stream:
        for line in stream:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            values[parts[0]] = " ".join(parts[1:])
    return values


def config_hash(values):
    semantic = {
        key: value for key, value in values.items()
        if key not in OUTPUT_KEYS and
        not key.endswith("_FILE") and
        key not in {"ALGORITHM", "SCENARIO", "SIM_SEED"}
    }
    encoded = json.dumps(semantic, sort_keys=True,
                         separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def registry_rows(source_hash):
    specs = [
        ("open_loop_pfc_configured", "open_loop_no_endhost_cc", 0,
         "open_loop_reference", 0, 0, 1, 0,
         "PFC configured but runtime pause behavior not verified"),
        ("open_loop_pfc_disabled", "open_loop_pfc_disabled", 0,
         "diagnostic_open_loop", 0, 0, 0, 1,
         "PFC generation disabled; ECN configuration retained"),
        ("dctcp", "DCTCP", 8, "formal_cc_baseline", 1, 1, 1, 0, ""),
        ("dcqcn", "DCQCN", 1, "formal_cc_baseline", 1, 1, 1, 0, ""),
        ("timely", "TIMELY", 7, "formal_cc_baseline", 1, 1, 1, 0, ""),
        ("hpcc_int", "HPCC-INT", 3, "formal_cc_baseline", 1, 1, 1, 0, ""),
        ("bop_qb", "BOP-QB", 15, "proposed_algorithm", 1, 0, 1, 0, ""),
        ("crfm_gate", "CRFM-Gate", 12, "ablation", 0, 0, 1, 0, ""),
        ("bop", "BOP", 13, "ablation", 0, 0, 1, 0, ""),
        ("dcqcn_wire_equalized", "DCQCN-Wire-Equalized", 17,
         "wire_diagnostic", 0, 0, 1, 1, ""),
    ]
    return [{
        "algorithm_name": name, "display_name": display,
        "cc_mode": mode, "baseline_class": cls,
        "formal_main": formal, "best_formal_cc_eligible": best,
        "pfc_configured": pfc, "diagnostic_only": diag,
        "frozen_control_logic": 1,
        "source_hash": source_hash, "semantic_note": note,
    } for name, display, mode, cls, formal, best, pfc, diag, note in specs]


def validate_reuse(row, v1_registry):
    scenario, algorithm, seed = row["scenario"], row["algorithm"], row["seed"]
    run_dir = V1 / "runs" / scenario / algorithm / ("seed_" + seed)
    reasons = []
    if not run_dir.is_dir():
        return None, ["missing_run_directory"]
    try:
        meta = json.load(open(run_dir / "run_meta.json"))
    except Exception:
        return None, ["invalid_run_meta"]
    if meta.get("scenario") != scenario:
        reasons.append("scenario")
    if meta.get("algorithm") != algorithm:
        reasons.append("algorithm")
    if int(meta.get("seed", -1)) != int(seed):
        reasons.append("seed")
    if int(meta.get("cc_mode", -1)) != CC_MODE[algorithm]:
        reasons.append("cc_mode")
    if meta.get("algorithm_source_hash") != v1_registry[algorithm]["source_hash"]:
        reasons.append("source_hash")
    if meta.get("exit_status") != 0 or meta.get("status") != "finished":
        reasons.append("exit_status")
    if not (run_dir / "completed.flag").exists():
        reasons.append("completed_flag")
    hashes = {}
    for name in ("topology.txt", "flow.txt", "rounds.txt",
                 "fixed_paths.txt", "trace.txt"):
        path = run_dir / name
        if not path.exists():
            reasons.append("missing_" + name)
            continue
        hashes[name] = sha(path)
        if meta.get("input_hashes", {}).get(name) != hashes[name]:
            reasons.append(name.replace(".txt", "") + "_hash")
    config = parse_config(run_dir / "config.txt")
    if int(config.get("CC_MODE", -1)) != CC_MODE[algorithm]:
        reasons.append("config_cc_mode")
    if config.get("PACKET_PAYLOAD_SIZE") != "1000":
        reasons.append("packet_payload")
    for key in ("KMIN_MAP", "KMAX_MAP", "PMAX_MAP", "BUFFER_SIZE",
                "USE_DYNAMIC_PFC_THRESHOLD", "ACK_HIGH_PRIO",
                "L2_ACK_INTERVAL", "RATE_AI", "RATE_HAI",
                "ALPHA_RESUME_INTERVAL", "RP_TIMER", "EWMA_GAIN",
                "FAST_RECOVERY_TIMES", "RATE_DECREASE_INTERVAL"):
        if key not in config:
            reasons.append("missing_" + key.lower())
    topology = (run_dir / "topology.txt").read_text()
    if "100Gbps" not in topology:
        reasons.append("link_rate")
    if not meta.get("scenario_meta", {}).get("fixed_ecmp"):
        reasons.append("fixed_path")
    record = {
        "run_id": row["run_id"], "section": row["section"],
        "scenario": scenario, "algorithm": algorithm, "seed": seed,
        "source_run": str(run_dir.relative_to(SIM)),
        "topology_hash": hashes.get("topology.txt", ""),
        "flow_hash": hashes.get("flow.txt", ""),
        "rounds_hash": hashes.get("rounds.txt", ""),
        "fixed_path_hash": hashes.get("fixed_paths.txt", ""),
        "source_hash": meta.get("algorithm_source_hash", ""),
        "algorithm_config_hash": config_hash(config),
        "packet_payload_bytes": config.get("PACKET_PAYLOAD_SIZE", ""),
        "ecn_threshold_config": config.get("KMIN_MAP", "") + "|" +
                                config.get("KMAX_MAP", ""),
        "pfc_threshold_config": config.get(
            "USE_DYNAMIC_PFC_THRESHOLD", "") + "|" +
                                config.get("BUFFER_SIZE", ""),
        "link_rate": "100Gbps" if "100Gbps" in topology else "UNKNOWN",
        "ack_config": config.get("L2_ACK_INTERVAL", "") + "|" +
                      config.get("ACK_HIGH_PRIO", ""),
        "cc_mode": config.get("CC_MODE", ""),
        "reuse_allowed": str(not reasons).lower(),
        "reuse_reject_reason": "|".join(sorted(set(reasons))),
    }
    return record, reasons


def main():
    CONFIG.mkdir(parents=True, exist_ok=True)
    source_hash = sha(SIM / "src/point-to-point/model/rdma-hw.cc")
    reg = registry_rows(source_hash)
    write_csv(CONFIG / "algorithm_registry.csv", list(reg[0]), reg)
    scenarios = read_csv(V1 / "config/main_scenarios.csv")
    write_csv(CONFIG / "main_scenarios.csv", list(scenarios[0]), scenarios)
    manifest = read_csv(V1 / "config/run_manifest.csv")
    formal = [r for r in manifest if
              (r["section"] == "main" and r["algorithm"] in FORMAL) or
              (r["section"] == "ablation" and r["algorithm"] in ABLATION) or
              r["section"] == "wire_fairness"]
    open_loop = []
    for row in manifest:
        if row["section"] == "main" and row["algorithm"] == "pfc_only":
            converted = dict(row)
            converted["source_algorithm"] = "pfc_only"
            converted["algorithm"] = "open_loop_pfc_configured"
            converted["run_id"] = converted["run_id"].replace(
                "__pfc_only__", "__open_loop_pfc_configured__")
            converted["baseline_class"] = "open_loop_reference"
            converted["formal_cc_baseline"] = "false"
            converted["runtime_pfc_status"] = "unverified"
            open_loop.append(converted)
    write_csv(CONFIG / "main_manifest.csv", list(formal[0]), formal)
    write_csv(CONFIG / "open_loop_reference_manifest.csv",
              list(open_loop[0]), open_loop)
    v1_reg = {r["algorithm_name"]: r for r in
              read_csv(V1 / "config/algorithm_registry.csv")}
    reuse = []
    for row in formal:
        record, _ = validate_reuse(row, v1_reg)
        if record is None:
            record = {
                "run_id": row["run_id"], "section": row["section"],
                "scenario": row["scenario"], "algorithm": row["algorithm"],
                "seed": row["seed"], "source_run": "",
                "topology_hash": "", "flow_hash": "", "rounds_hash": "",
                "fixed_path_hash": "", "source_hash": "",
                "algorithm_config_hash": "", "packet_payload_bytes": "",
                "ecn_threshold_config": "", "pfc_threshold_config": "",
                "link_rate": "", "ack_config": "", "cc_mode": "",
                "reuse_allowed": "false",
                "reuse_reject_reason": "missing_run_directory",
            }
        reuse.append(record)
    write_csv(CONFIG / "reuse_manifest.csv", list(reuse[0]), reuse)
    replay = []
    for seed in (1, 2, 3):
        source = V1 / "runs/n32_64k_g50/dcqcn" / ("seed_%d" % seed)
        meta = json.load(open(source / "run_meta.json"))
        replay.append({
            "scenario": "n32_64k_g50", "algorithm": "dcqcn",
            "seed": str(seed), "cc_mode": "1",
            "source_run": str(source.relative_to(SIM)),
            "replay_run":
                "bop_exp/main_v2/n32_dcqcn_replay/seed_%d" % seed,
            "topology_sha256": sha(source / "topology.txt"),
            "flow_sha256": sha(source / "flow.txt"),
            "rounds_sha256": sha(source / "rounds.txt"),
            "fixed_paths_sha256": sha(source / "fixed_paths.txt"),
            "trace_sha256": sha(source / "trace.txt"),
            "config_sha256": sha(source / "config.txt"),
            "algorithm_source_sha256":
                meta["algorithm_source_hash"],
            "status": "pending_manual_replay",
        })
    write_csv(CONFIG / "dcqcn_n32_replay_manifest.csv",
              list(replay[0]), replay)
    print("formal=%d open_loop=%d reuse_allowed=%d" % (
        len(formal), len(open_loop),
        sum(r["reuse_allowed"] == "true" for r in reuse)))


if __name__ == "__main__":
    main()
