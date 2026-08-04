#!/usr/bin/env python3
"""Deterministic input model for the frozen BOP-QB Clos experiments."""

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

ALGORITHMS = {
    "dctcp": 8,
    "dcqcn": 1,
    "timely": 7,
    "hpcc_int": 3,
    "bop_qb": 15,
}
FORBIDDEN = ("bop_qc", "bop_qb_max", "bop_qb_prt",
             "bop_qb_oracle_q0", "prt", "oracle")
PACKET_PAYLOAD_BYTES = 1000
BOP_PACKET_BYTES = 1024
LINK_BPS = 100_000_000_000
ECN_THRESHOLD_BYTES = 400_000
INITIAL_RELEASE_NS = 10_000_000
REGISTRATION_LEAD_NS = 10_000
SECOND_ITERATION_GAP_NS = 50_000


def digest(path):
    value = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def stable_seed(name, seed):
    text = ("%s:%d" % (name, seed)).encode("ascii")
    return int(hashlib.sha256(text).hexdigest()[:16], 16)


def split_bytes(total, count):
    base, remainder = divmod(int(total), int(count))
    return [base + (1 if index < remainder else 0)
            for index in range(count)]


def topology_spec(name):
    if name == "clos_1to1_64h":
        return {"name": name, "hosts": 64, "leaves": 8, "spines": 8,
                "oversubscription": "1:1"}
    if name == "clos_2to1_64h":
        return {"name": name, "hosts": 64, "leaves": 8, "spines": 4,
                "oversubscription": "2:1"}
    raise ValueError("unknown topology " + name)


def topology_model(name):
    spec = topology_spec(name)
    hosts = list(range(64))
    leaves = list(range(64, 72))
    spines = list(range(72, 72 + spec["spines"]))
    physical = []
    for host in hosts:
        physical.append((host, leaves[host // 8]))
    for leaf in leaves:
        for spine in spines:
            physical.append((leaf, spine))

    # ns-3 assigns interface indices in topology-file order, starting at one.
    next_if = {node: 1 for node in hosts + leaves + spines}
    directed = {}
    for left, right in physical:
        directed[(left, right)] = next_if[left]
        directed[(right, left)] = next_if[right]
        next_if[left] += 1
        next_if[right] += 1

    links = []
    by_edge = {}
    link_id = 0
    # Host NIC outputs are also shared by the many QPs of an all-to-all rank.
    # They have no switch INT hop; the global barrier guarantees q0=0 there.
    for host in hosts:
        leaf = leaves[host // 8]
        row = (link_id, host, directed[(host, leaf)], host, leaf, False)
        links.append(row)
        by_edge[(host, leaf)] = link_id
        link_id += 1
    # Every switch output traversed by DATA is controlled and INT-observable.
    for leaf in leaves:
        for host in range((leaf - 64) * 8, (leaf - 64) * 8 + 8):
            row = (link_id, leaf, directed[(leaf, host)], leaf, host, True)
            links.append(row)
            by_edge[(leaf, host)] = link_id
            link_id += 1
        for spine in spines:
            row = (link_id, leaf, directed[(leaf, spine)], leaf, spine, True)
            links.append(row)
            by_edge[(leaf, spine)] = link_id
            link_id += 1
    for spine in spines:
        for leaf in leaves:
            row = (link_id, spine, directed[(spine, leaf)], spine, leaf, True)
            links.append(row)
            by_edge[(spine, leaf)] = link_id
            link_id += 1
    return {
        "spec": spec, "hosts": hosts, "leaves": leaves, "spines": spines,
        "physical": physical, "directed_if": directed,
        "controlled_links": links, "edge_to_link": by_edge,
    }


def fixed_path(model, src, dst, spine):
    src_leaf = 64 + src // 8
    dst_leaf = 64 + dst // 8
    edges = [(src, src_leaf)]
    if src_leaf != dst_leaf:
        edges.extend(((src_leaf, spine), (spine, dst_leaf)))
    edges.append((dst_leaf, dst))
    return [model["edge_to_link"][edge] for edge in edges]


def alltoall_groups(participants, bytes_per_rank, iterations=1):
    groups = []
    ranks = list(range(participants))
    for iteration in range(iterations):
        transmissions = []
        for src in ranks:
            destinations = [dst for dst in ranks if dst != src]
            pieces = split_bytes(bytes_per_rank, len(destinations))
            transmissions.extend((src, dst, size)
                                 for dst, size in zip(destinations, pieces))
        groups.append({
            "stage": "all_to_all", "step": 0, "iteration": iteration,
            "transmissions": transmissions,
            "gap_ns": SECOND_ITERATION_GAP_NS if iteration else 0,
        })
    return groups


def ring_groups(participants, bytes_per_rank, iterations=1,
                stage_prefix="ring"):
    chunks = split_bytes(bytes_per_rank, participants)
    groups = []
    for iteration in range(iterations):
        for phase in ("reduce_scatter", "all_gather"):
            for step in range(participants - 1):
                transmissions = []
                for src in range(participants):
                    dst = (src + 1) % participants
                    chunk_index = ((src - step) % participants
                                   if phase == "reduce_scatter"
                                   else (src - step + 1) % participants)
                    transmissions.append((src, dst, chunks[chunk_index]))
                groups.append({
                    "stage": "%s_%s" % (stage_prefix, phase),
                    "step": step, "iteration": iteration,
                    "transmissions": transmissions,
                    "gap_ns": (SECOND_ITERATION_GAP_NS
                               if iteration and phase == "reduce_scatter"
                               and step == 0 else 0),
                })
    return groups


def hierarchical_groups(participants, bytes_per_rank, iterations=1,
                        stage_prefix="hierarchical"):
    if participants not in (32, 64):
        raise ValueError("hierarchical participant count must be 32 or 64")
    leaf_count = participants // 8
    local_chunk = split_bytes(bytes_per_rank, 8)
    # Local reduce-scatter leaves each local rank responsible for one eighth
    # of the tensor.  The inter-leaf ring operates on that shard, not on a
    # second full tensor.
    inter_chunks = [split_bytes(local_chunk[local], leaf_count)
                    for local in range(8)]
    groups = []
    for iteration in range(iterations):
        for phase in ("local_reduce_scatter",):
            for step in range(7):
                transmissions = []
                for leaf in range(leaf_count):
                    base = leaf * 8
                    for local in range(8):
                        src, dst = base + local, base + (local + 1) % 8
                        transmissions.append(
                            (src, dst, local_chunk[(local - step) % 8]))
                groups.append({
                    "stage": "%s_%s" % (stage_prefix, phase),
                    "step": step, "iteration": iteration,
                    "transmissions": transmissions,
                    "gap_ns": (SECOND_ITERATION_GAP_NS
                               if iteration and step == 0 else 0),
                })
        for phase in ("inter_reduce_scatter", "inter_all_gather"):
            for step in range(leaf_count - 1):
                transmissions = []
                for local in range(8):
                    for leaf in range(leaf_count):
                        src = leaf * 8 + local
                        dst = ((leaf + 1) % leaf_count) * 8 + local
                        index = ((leaf - step) % leaf_count
                                 if phase == "inter_reduce_scatter"
                                 else (leaf - step + 1) % leaf_count)
                        transmissions.append(
                            (src, dst, inter_chunks[local][index]))
                groups.append({
                    "stage": "%s_%s" % (stage_prefix, phase),
                    "step": step, "iteration": iteration,
                    "transmissions": transmissions, "gap_ns": 0,
                })
        for phase in ("local_all_gather",):
            for step in range(7):
                transmissions = []
                for leaf in range(leaf_count):
                    base = leaf * 8
                    for local in range(8):
                        src, dst = base + local, base + (local + 1) % 8
                        transmissions.append(
                            (src, dst, local_chunk[(local - step + 1) % 8]))
                groups.append({
                    "stage": "%s_%s" % (stage_prefix, phase),
                    "step": step, "iteration": iteration,
                    "transmissions": transmissions, "gap_ns": 0,
                })
    return groups


def scenario_specs():
    values = []
    collectives = ("all_to_all", "ring_allreduce_1d",
                   "hierarchical_allreduce_2d")
    for participants in (32, 64):
        for message_label, message_bytes in (
                ("1MiB", 1 << 20), ("64MiB", 64 << 20)):
            for collective in collectives:
                values.append({
                    "scenario": "c1_%s_n%d_%s" % (
                        collective, participants, message_label.lower()),
                    "topology": "clos_1to1_64h",
                    "collective": collective, "participants": participants,
                    "message_label": message_label,
                    "message_bytes_per_rank": message_bytes,
                    "iterations": 2, "section": "clos_1to1",
                    "synthetic_sequence": False,
                })
    values.append({
        "scenario": "dlrm_like_64h", "topology": "clos_1to1_64h",
        "collective": "dlrm_like", "participants": 64,
        "message_label": "8MiB_then_109.5MiB",
        "message_bytes_per_rank": 0, "iterations": 1,
        "section": "dlrm_like", "synthetic_sequence": True,
    })
    for collective in collectives:
        values.append({
            "scenario": "c2_%s_n64_64mib" % collective,
            "topology": "clos_2to1_64h",
            "collective": collective, "participants": 64,
            "message_label": "64MiB",
            "message_bytes_per_rank": 64 << 20,
            "iterations": 2, "section": "clos_2to1",
            "synthetic_sequence": False,
        })
    return values


def build_groups(spec):
    name = spec["collective"]
    n = spec["participants"]
    size = spec["message_bytes_per_rank"]
    iterations = spec["iterations"]
    if name == "all_to_all":
        return alltoall_groups(n, size, iterations)
    if name == "ring_allreduce_1d":
        return ring_groups(n, size, iterations)
    if name == "hierarchical_allreduce_2d":
        return hierarchical_groups(n, size, iterations)
    if name == "dlrm_like":
        first = alltoall_groups(n, 8 << 20, 1)
        second = hierarchical_groups(n, int(109.5 * (1 << 20)), 1,
                                     "dlrm_hierarchical")
        second[0]["gap_ns"] = 50_000
        return first + second
    raise ValueError("unknown collective " + name)


def materialize(spec, seed):
    model = topology_model(spec["topology"])
    raw_groups = build_groups(spec)
    rng = random.Random(stable_seed(spec["scenario"], seed))
    qp_ids = {}
    qp_rounds = {}
    qp_total = {}
    paths = {}
    forced_spines = {}
    group_rows = []
    schedule_rows = []
    spines = model["spines"]
    for group_id, raw in enumerate(raw_groups):
        members = []
        for src, dst, size in raw["transmissions"]:
            key = (src, dst)
            if key not in qp_ids:
                qp_ids[key] = len(qp_ids)
                qp_rounds[key] = []
                qp_total[key] = 0
                spine = -1 if src // 8 == dst // 8 else rng.choice(spines)
                forced_spines[qp_ids[key]] = spine
                paths[qp_ids[key]] = fixed_path(model, src, dst, spine)
            members.append((key, int(size)))
        participant_count = len(members)
        predecessor = group_id - 1
        initial = INITIAL_RELEASE_NS if group_id == 0 else 0
        group_rows.append((group_id, predecessor, raw["gap_ns"], initial))
        sender_jitter = {
            rank: rng.randint(0, 5000)
            for rank in sorted(set(src for (src, _dst), _size in members))
        }
        for key, size in members:
            flow_id = qp_ids[key]
            round_id = len(qp_rounds[key])
            src, _dst = key
            row = (flow_id, round_id, group_id, participant_count, size,
                   raw["gap_ns"], sender_jitter[src], src, initial)
            qp_rounds[key].append(row)
            qp_total[key] += size
        schedule_rows.append({
            "group_id": group_id, "predecessor_group_id": predecessor,
            "iteration": raw["iteration"], "stage": raw["stage"],
            "step": raw["step"], "compute_gap_ns": raw["gap_ns"],
            "participant_count": participant_count,
            "total_payload_bytes": sum(size for _key, size in members),
        })
    flows = [None] * len(qp_ids)
    rounds = []
    for key, flow_id in qp_ids.items():
        src, dst = key
        flows[flow_id] = (src, dst, qp_total[key])
        rounds.extend(qp_rounds[key])
    rounds.sort(key=lambda row: (row[0], row[1]))
    return {
        "model": model, "flows": flows, "rounds": rounds,
        "paths": paths, "forced_spines": forced_spines,
        "groups": group_rows, "schedule": schedule_rows,
    }


def write_csv(path, fieldnames, rows):
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames,
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def input_hashes(case_dir):
    names = ("topology.txt", "flow.txt", "rounds.txt", "fixed_paths.txt",
             "multilink_links.txt", "multilink_paths.txt",
             "group_schedule.txt", "collective_schedule.csv", "trace.txt")
    return {name: digest(os.path.join(case_dir, name)) for name in names}


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, int(math.ceil(fraction * len(ordered))) - 1)]


def read_csv(path):
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def multilink_plan(flow_bytes, flow_paths, links, max_rates,
                   rho=1.0, packet_bytes=BOP_PACKET_BYTES):
    """Python mirror of the implemented, parameter-frozen C++ formula."""
    runtime = {}
    for flow_id, amount in flow_bytes.items():
        for link_id in flow_paths[flow_id]:
            state = runtime.setdefault(link_id, {
                "workload": 0, "flow_count": 0, "credit": 0})
            state["workload"] += amount
            state["flow_count"] += 1
    t_line = max(8.0 * flow_bytes[f] / max_rates[f] for f in flow_bytes)
    alpha = 1.0
    for link_id, state in runtime.items():
        link = links[link_id]
        q0 = link.get("q0", 0)
        available = rho * link["capacity"] - link.get("background", 0)
        state["t_link"] = 8.0 * (q0 + state["workload"]) / available
        target = int(math.floor(.5 * link["ecn_threshold"]))
        state["room"] = max(target - q0 -
                            state["flow_count"] * packet_bytes, 0)
        alpha = min(alpha, state["room"] / state["workload"])
    t_star = max([t_line] + [state["t_link"]
                             for state in runtime.values()])
    rates = {flow_id: min(max_rates[flow_id],
                          max(1, int(math.floor(
                              8.0 * amount / t_star))))
             for flow_id, amount in flow_bytes.items()}
    credits = {flow_id: int(math.floor(alpha * amount))
               for flow_id, amount in flow_bytes.items()}
    for flow_id, credit in credits.items():
        for link_id in flow_paths[flow_id]:
            runtime[link_id]["credit"] += credit
    target = int(math.floor(alpha * sum(flow_bytes.values())))
    remainder = target - sum(credits.values())
    while remainder:
        progressed = False
        for flow_id in sorted(flow_bytes):
            if not remainder:
                break
            if credits[flow_id] >= flow_bytes[flow_id]:
                continue
            if any(runtime[link_id]["credit"] >= runtime[link_id]["room"]
                   for link_id in flow_paths[flow_id]):
                continue
            credits[flow_id] += 1
            remainder -= 1
            progressed = True
            for link_id in flow_paths[flow_id]:
                runtime[link_id]["credit"] += 1
        if not progressed:
            raise AssertionError("infeasible deterministic remainder")
    # Rebuild credit totals because the floor allocation preceded runtime use.
    for state in runtime.values():
        state["credit"] = 0
    for flow_id, credit in credits.items():
        for link_id in flow_paths[flow_id]:
            runtime[link_id]["credit"] += credit
    return {"t_star": t_star, "rates": rates, "alpha": alpha,
            "credits": credits, "links": runtime}
