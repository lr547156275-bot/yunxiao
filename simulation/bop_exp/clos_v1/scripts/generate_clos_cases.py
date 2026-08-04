#!/usr/bin/env python3
"""Generate all deterministic blueprints and the exact 240-run manifest."""

import csv
import json
import os
import shutil
import sys

from closlib import (ALGORITHMS, BOP_PACKET_BYTES, CASES, CONFIG,
                     ECN_THRESHOLD_BYTES, INITIAL_RELEASE_NS, LINK_BPS,
                     PACKET_PAYLOAD_BYTES, build_groups, input_hashes,
                     materialize, scenario_specs, topology_model, write_csv)


def base_config(stop_seconds):
    return """ENABLE_QCN 1
USE_DYNAMIC_PFC_THRESHOLD 1
CLAMP_TARGET_RATE 0
PAUSE_TIME 5
DATA_RATE 100Gbps
LINK_DELAY 0.001ms
PACKET_PAYLOAD_SIZE 1000
L2_CHUNK_SIZE 4000
L2_ACK_INTERVAL 1
L2_BACK_TO_ZERO 0
TOPOLOGY_FILE topology.txt
FLOW_FILE flow.txt
FIXED_PATH_FILE fixed_paths.txt
TRACE_FILE trace.txt
TRACE_OUTPUT_FILE /dev/null
SIMULATOR_STOP_TIME {stop}
CC_MODE 15
ALPHA_RESUME_INTERVAL 55
RATE_DECREASE_INTERVAL 4
RP_TIMER 300
EWMA_GAIN 0.00390625
FAST_RECOVERY_TIMES 5
RATE_AI 50Mb/s
RATE_HAI 100Mb/s
MIN_RATE 100Mb/s
DCTCP_RATE_AI 1000Mb/s
ERROR_RATE_PER_LINK 0
HAS_WIN 1
GLOBAL_T 1
MI_THRESH 5
VAR_WIN 0
FAST_REACT 1
U_TARGET 0.95
INT_MULTI 1
RATE_BOUND 1
ACK_HIGH_PRIO 0
LINK_DOWN 0 0 0
ENABLE_TRACE 0
BUFFER_SIZE 32
QLEN_MON_FILE /dev/null
QLEN_MON_START 1000000000
QLEN_MON_END 1000000001
KMAX_MAP 1 100000000000 1600
KMIN_MAP 1 100000000000 400
PMAX_MAP 1 100000000000 0.2
MULTI_RATE 1
SAMPLE_FEEDBACK 0
ROUND_SCHEDULE_FILE rounds.txt
ROUND_MODE 1
ROUND_TRACE_SELECTED_FLOWS 0,1,2,3
CRFM_TRACE_SAMPLE_US 100
CRFM_MAX_TRACE_FILE_MB 64
CRFM_MAX_TRACE_TOTAL_MB 128
CRFM_MIN_FREE_GB 5
CRFM_MAX_EVENT_ROWS 100000
CRFM_DEBUG 0
BOP_RHO 1.0
BOP_BACKGROUND_BPS 0
BOP_PHASE_STAGGER 1
BOP_PACKET_BYTES 1024
BOP_BOTTLENECK_BPS 100000000000
BOP_QB_QUEUE_FRACTION 0.50
BOP_QB_PACKET_MARGIN 1
BOP_QB_ENABLE_PHASE_STAGGER 1
BOP_MULTILINK_ENABLE 1
BOP_MULTILINK_LINK_FILE multilink_links.txt
BOP_MULTILINK_PATH_FILE multilink_paths.txt
BOP_MULTILINK_GROUP_FILE group_schedule.txt
""".format(stop=stop_seconds)


def write_case(spec, seed):
    case_dir = os.path.join(CASES, spec["scenario"], "seed_%d" % seed)
    os.makedirs(case_dir, exist_ok=True)
    data = materialize(spec, seed)
    model = data["model"]
    node_count = 64 + 8 + model["spec"]["spines"]
    with open(os.path.join(case_dir, "topology.txt"), "w") as handle:
        switches = model["leaves"] + model["spines"]
        handle.write("%d %d %d\n" % (
            node_count, len(switches), len(model["physical"])))
        handle.write(" ".join(str(value) for value in switches) + "\n")
        for left, right in model["physical"]:
            handle.write("%d %d 100Gbps 0.001ms 0\n" % (left, right))
    with open(os.path.join(case_dir, "flow.txt"), "w") as handle:
        handle.write("%d\n" % len(data["flows"]))
        registration = (INITIAL_RELEASE_NS - 10_000) * 1e-9
        for src, dst, total in data["flows"]:
            handle.write("%d %d 3 100 %d %.9f\n" % (
                src, dst, total, registration))
    with open(os.path.join(case_dir, "rounds.txt"), "w") as handle:
        handle.write("%d\n" % len(data["rounds"]))
        for row in data["rounds"]:
            handle.write(" ".join(str(value) for value in row) + "\n")
    with open(os.path.join(case_dir, "fixed_paths.txt"), "w") as handle:
        for flow_id in range(len(data["flows"])):
            handle.write("%d %d\n" % (
                flow_id, data["forced_spines"][flow_id]))
    with open(os.path.join(case_dir, "multilink_links.txt"), "w") as handle:
        handle.write("%d\n" % len(model["controlled_links"]))
        for link_id, node, interface, _left, _right, telemetry in \
                model["controlled_links"]:
            handle.write("%d %d %d %d %d 0 %d\n" % (
                link_id, node, interface, LINK_BPS, ECN_THRESHOLD_BYTES,
                1 if telemetry else 0))
    with open(os.path.join(case_dir, "multilink_paths.txt"), "w") as handle:
        handle.write("%d\n" % len(data["paths"]))
        for flow_id in range(len(data["paths"])):
            path = data["paths"][flow_id]
            handle.write("%d %d %s\n" % (
                flow_id, len(path), " ".join(str(value) for value in path)))
    with open(os.path.join(case_dir, "group_schedule.txt"), "w") as handle:
        handle.write("%d\n" % len(data["groups"]))
        for row in data["groups"]:
            handle.write(" ".join(str(value) for value in row) + "\n")
    write_csv(os.path.join(case_dir, "collective_schedule.csv"),
              ["group_id", "predecessor_group_id", "iteration", "stage",
               "step", "compute_gap_ns", "participant_count",
               "total_payload_bytes"], data["schedule"])
    with open(os.path.join(case_dir, "trace.txt"), "w") as handle:
        handle.write("0\n")
    stop = 1.0 if spec["topology"] == "clos_2to1_64h" else 0.7
    with open(os.path.join(case_dir, "config.txt"), "w") as handle:
        handle.write(base_config(stop))
    meta = dict(spec)
    meta.update({
        "seed": seed,
        "description": ("size-driven synthetic communication sequence; "
                        "not a real GPU training trace"
                        if spec["synthetic_sequence"] else
                        "deterministic synthetic collective"),
        "host_count": 64, "leaf_count": 8,
        "spine_count": model["spec"]["spines"],
        "host_leaf_rate_bps": LINK_BPS,
        "leaf_spine_rate_bps": LINK_BPS,
        "link_delay": "0.001ms", "buffer_size_mb": 32,
        "ecn_kmin_kb": 400, "ecn_kmax_kb": 1600,
        "pmax": 0.2, "packet_payload_bytes": PACKET_PAYLOAD_BYTES,
        "bop_packet_bytes": BOP_PACKET_BYTES,
        "bop_rho": 1.0, "bop_background_bps": 0,
        "bop_qb_queue_fraction": 0.5,
        "first_release_ns": INITIAL_RELEASE_NS,
        "same_qp_continuous_sequence": True,
        "global_barrier_every_group": True,
    })
    with open(os.path.join(case_dir, "scenario_meta.json"), "w") as handle:
        json.dump(meta, handle, indent=2, sort_keys=True)
        handle.write("\n")
    hashes = input_hashes(case_dir)
    with open(os.path.join(case_dir, "input_hashes.json"), "w") as handle:
        json.dump(hashes, handle, indent=2, sort_keys=True)
        handle.write("\n")


def generate():
    os.makedirs(CONFIG, exist_ok=True)
    os.makedirs(CASES, exist_ok=True)
    specs = scenario_specs()
    topologies = []
    for name in ("clos_1to1_64h", "clos_2to1_64h"):
        model = topology_model(name)
        topologies.append({
            "topology": name, "hosts": 64, "leaves": 8,
            "hosts_per_leaf": 8, "spines": model["spec"]["spines"],
            "host_leaf_bps": LINK_BPS, "leaf_spine_bps": LINK_BPS,
            "oversubscription": model["spec"]["oversubscription"],
            "link_delay": "0.001ms",
        })
    write_csv(os.path.join(CONFIG, "topology_registry.csv"),
              list(topologies[0]), topologies)
    collectives = [
        {"collective": "all_to_all",
         "definition": "per-rank bytes split across N-1 destinations"},
        {"collective": "ring_allreduce_1d",
         "definition": "N-1 reduce-scatter plus N-1 all-gather barriers"},
        {"collective": "hierarchical_allreduce_2d",
         "definition": "7 local RS, inter-leaf ring AR, 7 local AG"},
        {"collective": "dlrm_like",
         "definition": "synthetic 8MiB A2A, 50us, 109.5MiB hierarchical AR"},
    ]
    write_csv(os.path.join(CONFIG, "collective_registry.csv"),
              ["collective", "definition"], collectives)
    manifest_rows = []
    for spec in specs:
        manifest_rows.append(dict(spec))
        for seed in (1, 2, 3):
            write_case(spec, seed)
    write_csv(os.path.join(CONFIG, "scenario_manifest.csv"),
              list(manifest_rows[0]), manifest_rows)
    run_rows = []
    for spec in specs:
        for algorithm in ALGORITHMS:
            for seed in (1, 2, 3):
                run_id = "%s__%s__%d__%s__%s__seed%d" % (
                    spec["topology"], spec["collective"],
                    spec["participants"], spec["message_label"],
                    algorithm, seed)
                run_rows.append({
                    "run_id": run_id, "section": spec["section"],
                    "scenario": spec["scenario"],
                    "topology": spec["topology"],
                    "collective": spec["collective"],
                    "participants": spec["participants"],
                    "message": spec["message_label"],
                    "algorithm": algorithm, "cc_mode": ALGORITHMS[algorithm],
                    "seed": seed,
                })
    write_csv(os.path.join(CONFIG, "run_manifest.csv"),
              list(run_rows[0]), run_rows)
    print("generated scenarios=%d runs=%d per_seed=%d" % (
        len(specs), len(run_rows), len(run_rows) // 3))


if __name__ == "__main__":
    generate()
