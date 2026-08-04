#!/usr/bin/env python3
import csv
import hashlib
import json
import math
import os
import random

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SIM_ROOT = os.path.abspath(os.path.join(ROOT, "..", ".."))
CONFIG = os.path.join(ROOT, "config")
CASES = os.path.join(ROOT, "cases")

MAIN_ALGOS = ("pfc_only", "dctcp", "dcqcn", "timely", "hpcc_int",
              "bop_qb")
FORBIDDEN_MAIN = ("bop_qc", "bop_qb_max", "bop_qb_prt",
                  "bop_qb_oracle_q0")


def rows(path):
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def digest(path):
    value = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1048576), b""):
            value.update(block)
    return value.hexdigest()


def stable_seed(scenario, seed):
    return int(hashlib.sha256(
        ("%s:%d" % (scenario, seed)).encode("ascii")).hexdigest()[:16], 16)


def registry():
    return {row["algorithm_name"]: row for row in rows(
        os.path.join(CONFIG, "algorithm_registry.csv"))}


def scenarios(include_single=True):
    result = {row["scenario"]: row for row in rows(
        os.path.join(CONFIG, "main_scenarios.csv"))}
    if include_single:
        result["single_round_n16_64k"] = {
            "scenario": "single_round_n16_64k", "sweep": "wire_fairness",
            "senders": "16", "rounds": "1", "compute_gap_us": "0",
            "min_message_bytes": "65536", "max_message_bytes": "65536",
            "mean_message_bytes": "65536", "message_size_ratio": "1.0",
            "coefficient_of_variation": "0.0",
            "total_group_payload_bytes": "1048576",
            "simulator_stop_time_s": "0.05",
        }
    return result


def flow_sizes(spec):
    n = int(spec["senders"])
    scenario = spec["scenario"]
    if scenario == "hetero_mild":
        return [65536] * 8 + [196608] * 8
    if scenario == "hetero_strong":
        return [16384] * 8 + [245760] * 8
    return [int(spec["mean_message_bytes"])] * n


def write_round_inputs(case_dir, spec, seed):
    rng = random.Random(stable_seed(spec["scenario"], seed))
    n, count = int(spec["senders"]), int(spec["rounds"])
    gap_ns = int(spec["compute_gap_us"]) * 1000
    sizes = flow_sizes(spec)
    first_ns = 10000000
    values = []
    for flow in range(n):
        for round_id in range(count):
            # A zero compute gap cannot legally combine with negative jitter
            # because the global barrier is a hard lower bound.
            jitter = rng.randint(0 if gap_ns == 0 else -5000, 5000)
            values.append((flow, round_id, round_id, n, sizes[flow],
                           0 if round_id == 0 else gap_ns, jitter, flow,
                           first_ns if round_id == 0 else 0))
    with open(os.path.join(case_dir, "rounds.txt"), "w") as handle:
        handle.write("%d\n" % len(values))
        for value in values:
            handle.write(" ".join(str(item) for item in value) + "\n")
    registration = (first_ns - 10000) * 1e-9
    with open(os.path.join(case_dir, "flow.txt"), "w") as handle:
        handle.write("%d\n" % n)
        for flow in range(n):
            handle.write("%d %d 3 100 %d %.9f\n" % (
                flow, n, count * sizes[flow], registration))


def write_topology(case_dir, n):
    receiver, src_leaf, dst_leaf = n, n + 1, n + 2
    spine_a, spine_b = n + 3, n + 4
    links = [(sender, src_leaf) for sender in range(n)]
    links += [(receiver, dst_leaf), (src_leaf, spine_a),
              (src_leaf, spine_b), (spine_a, dst_leaf),
              (spine_b, dst_leaf)]
    with open(os.path.join(case_dir, "topology.txt"), "w") as handle:
        handle.write("%d 4 %d\n" % (n + 5, len(links)))
        handle.write("%d %d %d %d\n" % (
            src_leaf, dst_leaf, spine_a, spine_b))
        for left, right in links:
            handle.write("%d %d 100Gbps 0.001ms 0\n" % (left, right))
    with open(os.path.join(case_dir, "fixed_paths.txt"), "w") as handle:
        for sender in range(n):
            handle.write("%d %d\n" % (
                sender, spine_a if sender % 2 == 0 else spine_b))
    with open(os.path.join(case_dir, "trace.txt"), "w") as handle:
        handle.write("0\n")
    return receiver, dst_leaf


def base_config(spec, bottleneck):
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
ROUND_TRACE_SELECTED_LINKS {bottleneck}:1
CRFM_TRACE_SAMPLE_US 10
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
""".format(stop=spec["simulator_stop_time_s"], bottleneck=bottleneck)


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, int(math.ceil(fraction * len(ordered))) - 1)
    return ordered[index]
