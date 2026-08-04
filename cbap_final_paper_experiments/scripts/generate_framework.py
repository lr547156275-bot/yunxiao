#!/usr/bin/env python3
"""Generate the preregistered CBAP final-paper inputs; never runs ns-3."""
import csv
import hashlib
import importlib.util
import json
import os
import random
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(ROOT, ".."))
CASES = os.path.join(ROOT, "configs", "cases")
MANIFESTS = os.path.join(ROOT, "manifests")
V12_GENERATOR = os.path.join(REPO, "cbap_exp_v12_scoped", "scripts",
                             "generate_framework.py")
PARKING_SOURCE = os.path.join(REPO, "cbap_exp_v11_freeze", "cases",
                              "e4_parking_lot", "synchronous")
CLOS_SCRIPTS = os.path.join(REPO, "simulation", "bop_exp", "clos_v1",
                            "scripts")

FORMAL = {
    "dctcp": (8, "baseline", "ALWAYS", 0),
    "dcqcn": (1, "baseline", "ALWAYS", 0),
    "timely": (7, "baseline", "ALWAYS", 0),
    "hpcc_int": (3, "baseline", "ALWAYS", 0),
    "bop_qb": (15, "bop_qb_v1", "ALWAYS", 0),
    "independent_min_grant": (20, "v1", "ALWAYS", 0),
    "cbap_full_v13_ratefloor_fix": (
        25, "v1.3", "SHARED_BATCH_OVERSUBSCRIPTION", 1),
}
ABLATION = {
    "cbap_init_only": (21, "v1.1", "ALWAYS", 0),
    "cbap_rateonly_v11": (22, "v1.1", "ALWAYS", 0),
    "cbap_full_v14_stable_handoff": (
        26, "v1.4", "SHARED_BATCH_OVERSUBSCRIPTION", 1),
    "cbap_full_v15_guarded_delegation": (
        27, "v1.5", "SHARED_BATCH_OVERSUBSCRIPTION", 1),
}
MESSAGE = {"64k": 64 << 10, "256k": 256 << 10,
           "1m": 1 << 20, "4m": 4 << 20, "64m": 64 << 20}
FIELDS = [
    "run_id", "experiment_family", "scenario_id", "algorithm", "seed",
    "fanin", "message_bytes", "incumbent_load", "release_skew_us",
    "topology", "workload", "oversubscription", "expected_scope",
    "cc_mode", "cbap_version", "scope_policy", "rate_floor_policy",
    "case_dir", "config_hash", "flow_hash", "path_hash", "random_input_hash",
    "git_commit",
]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V12 = load_module("cbap_final_v12_generator", V12_GENERATOR)
sys.path.insert(0, CLOS_SCRIPTS)
import closlib  # noqa: E402
import generate_clos_cases as old_clos_generator  # noqa: E402


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def stable_seed(*parts):
    return int(hashlib.sha256("::".join(map(str, parts)).encode()).hexdigest()[:16], 16)


def git_commit():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO,
                                   text=True).strip()


def rewrite(path, updates):
    lines, seen = [], set()
    for line in open(path):
        words = line.split()
        key = words[0] if words and not words[0].startswith("#") else ""
        if key in updates:
            lines.append("%s %s\n" % (key, updates[key])); seen.add(key)
        else:
            lines.append(line)
    for key in sorted(set(updates) - seen):
        lines.append("%s %s\n" % (key, updates[key]))
    with open(path, "w") as stream:
        stream.writelines(lines)


def dump(path, value):
    with open(path, "w") as stream:
        json.dump(value, stream, indent=2, sort_keys=True); stream.write("\n")


def write_csv(path, fields, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def refresh_case(case, meta_updates=None):
    meta_path = os.path.join(case, "scenario_meta.json")
    meta = json.load(open(meta_path)) if os.path.isfile(meta_path) else {}
    if meta_updates:
        meta.update(meta_updates)
    dump(meta_path, meta)
    names = [name for name in sorted(os.listdir(case))
             if os.path.isfile(os.path.join(case, name)) and
             name not in ("input_hashes.json", "v13_input_hashes.json")]
    dump(os.path.join(case, "input_hashes.json"),
         {name: sha(os.path.join(case, name)) for name in names})


def copy_case(src, dst):
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def mutate_round_jitter(case, offsets_ns):
    path = os.path.join(case, "rounds.txt")
    lines = [line.split() for line in open(path) if line.split()]
    out = ["%s\n" % lines[0][0]]
    for words in lines[1:]:
        fid = int(words[0])
        if fid in offsets_ns:
            words[6] = str(int(offsets_ns[fid]))
        out.append(" ".join(words) + "\n")
    with open(path, "w") as stream:
        stream.writelines(out)


def generate_star(case, scenario, fanin, message, load, offsets=None,
                  random_record=None, release_base_ns=3000000):
    V12.star_case(os.path.dirname(case), os.path.basename(case), fanin,
                  message, load, expected="ENABLE")
    incumbent_count = 1 if load else 0
    offsets = offsets or {}
    mutate_round_jitter(case, {incumbent_count + i: offsets.get(i, 0)
                               for i in range(fanin)})
    if release_base_ns != 3000000:
        rounds_path = os.path.join(case, "rounds.txt")
        lines = [line.split() for line in open(rounds_path) if line.split()]
        with open(rounds_path, "w") as stream:
            stream.write(lines[0][0] + "\n")
            for words in lines[1:]:
                if int(words[0]) >= incumbent_count: words[8] = str(release_base_ns)
                stream.write(" ".join(words) + "\n")
        group_path = os.path.join(case, "group_schedule.txt")
        groups = [line.split() for line in open(group_path) if line.split()]
        with open(group_path, "w") as stream:
            stream.write(groups[0][0] + "\n")
            for words in groups[1:]:
                if int(words[0]) == incumbent_count: words[3] = str(release_base_ns)
                stream.write(" ".join(words) + "\n")
    actual = [{"flow_id": incumbent_count + i,
               "release_offset_ns": int(offsets.get(i, 0)),
               "release_time_ns": release_base_ns + int(offsets.get(i, 0))}
              for i in range(fanin)]
    write_csv(os.path.join(case, "release_schedule.csv"),
              ["flow_id", "release_offset_ns", "release_time_ns"], actual)
    if random_record is not None:
        dump(os.path.join(case, "random_input.json"), random_record)
    rewrite(os.path.join(case, "config.txt"), {
        "SIMULATOR_STOP_TIME": "0.12",
        "CRFM_TRACE_SAMPLE_US": 10,
        "CBAP_SCOPE_POLICY": 0,
        "CBAP_RATE_FLOOR_POLICY": 0,
    })
    refresh_case(case, {
        "scenario": scenario, "family": "single_bottleneck",
        "pending_count": fanin, "message_bytes": message,
        "incumbent_offered_load_percent": load,
        "expected_scope_decision": "ENABLE", "fixed_path": True,
        "release_schedule_file": "release_schedule.csv",
        "nominal_common_release_ns": 3000000,
        "pending_flow_ids": list(range(incumbent_count, incumbent_count + fanin)),
        "incumbent_flow_ids": list(range(incumbent_count)),
    })


def row_for(family, scenario, algorithm, seed, case, fanin="",
            message="", load="", skew="", topology="star_100g",
            workload="synchronous_incast", oversub="1:1", expected="ENABLE"):
    all_algorithms = dict(FORMAL); all_algorithms.update(ABLATION)
    mode, version, scope, floor = all_algorithms[algorithm]
    config = os.path.join(case, "config.txt")
    flow = os.path.join(case, "flow.txt")
    paths = [os.path.join(case, n) for n in
             ("controlled_paths.txt", "multilink_paths.txt", "fixed_paths.txt")
             if os.path.isfile(os.path.join(case, n))]
    path_hash = hashlib.sha256("".join(sha(p) for p in paths).encode()).hexdigest()
    random_path = os.path.join(case, "random_input.json")
    run_id = "%s__%s__%s__seed%s" % (family, scenario, algorithm, seed)
    return {
        "run_id": run_id, "experiment_family": family,
        "scenario_id": scenario, "algorithm": algorithm, "seed": seed,
        "fanin": fanin, "message_bytes": message, "incumbent_load": load,
        "release_skew_us": skew, "topology": topology,
        "workload": workload, "oversubscription": oversub,
        "expected_scope": expected, "cc_mode": mode,
        "cbap_version": version, "scope_policy": scope,
        "rate_floor_policy": floor,
        "case_dir": os.path.relpath(case, ROOT),
        "config_hash": sha(config), "flow_hash": sha(flow),
        "path_hash": path_hash,
        "random_input_hash": sha(random_path) if os.path.isfile(random_path) else "",
        "git_commit": git_commit(),
    }


def generate_single_and_skew(rows_by_family):
    for fanin in (4, 8, 16, 32, 64):
        for label in ("64k", "256k", "1m", "4m"):
            for load in (0, 50, 80, 95):
                scenario = "fan%d_msg%s_load%d" % (fanin, label, load)
                case = os.path.join(CASES, "single_bottleneck", scenario)
                generate_star(case, scenario, fanin, MESSAGE[label], load)
                for algorithm in FORMAL:
                    rows_by_family["single_bottleneck"].append(row_for(
                        "single_bottleneck", scenario, algorithm, 1, case,
                        fanin, MESSAGE[label], load, 0))
    for fanin in (16, 64):
        for label in ("256k", "1m", "4m"):
            for load in (80, 95):
                for skew_us in (2, 5, 10, 20, 50):
                    scenario = "fan%d_msg%s_load%d_skew%dus" % (
                        fanin, label, load, skew_us)
                    rng = random.Random(stable_seed("skew", scenario))
                    offsets = {i: rng.randint(0, skew_us * 1000)
                               for i in range(fanin)}
                    case = os.path.join(CASES, "release_skew", scenario)
                    generate_star(case, scenario, fanin, MESSAGE[label], load,
                                  offsets)
                    refresh_case(case, {"family": "release_skew",
                                        "release_skew_us": skew_us})
                    for algorithm in FORMAL:
                        rows_by_family["release_skew"].append(row_for(
                            "release_skew", scenario, algorithm, 1, case,
                            fanin, MESSAGE[label], load, skew_us))


def edit_parking(case, scenario, message, delay_rtts=0, l1=100, l2=100):
    copy_case(PARKING_SOURCE, case)
    flow_lines = [line.split() for line in open(os.path.join(case, "flow.txt"))
                  if line.split()]
    with open(os.path.join(case, "flow.txt"), "w") as stream:
        stream.write(flow_lines[0][0] + "\n")
        for words in flow_lines[1:]:
            words[4] = str(message)
            stream.write(" ".join(words) + "\n")
    rounds = [line.split() for line in open(os.path.join(case, "rounds.txt"))
              if line.split()]
    with open(os.path.join(case, "rounds.txt"), "w") as stream:
        stream.write(rounds[0][0] + "\n")
        for words in rounds[1:]:
            words[4] = str(message)
            # F0 is flow 0 and crosses both controlled links.  Verified RTT is
            # 6 us for its three 1-us forward and reverse hops.
            if int(words[0]) == 0:
                words[6] = str(delay_rtts * 6000)
            stream.write(" ".join(words) + "\n")
    topology = os.path.join(case, "topology.txt")
    lines = []
    for line in open(topology):
        words = line.split()
        if len(words) >= 5 and words[0:2] == ["6", "7"]:
            words[2] = "%dGbps" % l1; line = " ".join(words) + "\n"
        if len(words) >= 5 and words[0:2] == ["7", "8"]:
            words[2] = "%dGbps" % l2; line = " ".join(words) + "\n"
        lines.append(line)
    with open(topology, "w") as stream: stream.writelines(lines)
    controlled = os.path.join(case, "controlled_links.txt")
    lines = [line.split() for line in open(controlled) if line.split()]
    with open(controlled, "w") as stream:
        stream.write(lines[0][0] + "\n")
        for words in lines[1:]:
            words[3] = str((l1 if words[0] == "1" else l2) * 1000000000)
            stream.write(" ".join(words) + "\n")
    rewrite(os.path.join(case, "config.txt"), {
        "SIMULATOR_STOP_TIME": "0.12", "CBAP_SCOPE_POLICY": 0,
        "CBAP_RATE_FLOOR_POLICY": 0,
        "KMAX_MAP": "2 80000000000 1600 100000000000 1600",
        "KMIN_MAP": "2 80000000000 400 100000000000 400",
        "PMAX_MAP": "2 80000000000 0.2 100000000000 0.2",
    })
    refresh_case(case, {
        "scenario": scenario, "family": "multibottleneck",
        "subcase": scenario, "message_bytes": message,
        "flow_sizes_bytes": [message, message, message],
        "application_ready_times_s": [
            .003 + delay_rtts * .000006, .003, .003],
        "incumbent_offered_load_percent": 80,
        "f0_delay_rtts": delay_rtts, "l1_capacity_gbps": l1,
        "l2_capacity_gbps": l2, "rtt_us": 6,
        "pending_flow_ids": [0, 1, 2], "incumbent_flow_ids": [],
        "capacity_bps": min(l1, l2) * 1000000000,
        "expected_scope_decision": "ENABLE",
    })


def generate_multibottleneck(rows_by_family):
    specs = [
        ("parking_sync_1m_load80", MESSAGE["1m"], 0, 100, 100),
        ("parking_sync_4m_load80", MESSAGE["4m"], 0, 100, 100),
        ("parking_f0delay4rtt_1m_load80", MESSAGE["1m"], 4, 100, 100),
        ("parking_f0delay4rtt_4m_load80", MESSAGE["4m"], 4, 100, 100),
        ("parking_f0delay6rtt_1m_load80", MESSAGE["1m"], 6, 100, 100),
        ("parking_f0delay6rtt_4m_load80", MESSAGE["4m"], 6, 100, 100),
        ("parking_asym_l1_100_l2_80_1m", MESSAGE["1m"], 0, 100, 80),
        ("parking_asym_l1_80_l2_100_4m", MESSAGE["4m"], 0, 80, 100),
    ]
    for scenario, message, delay, l1, l2 in specs:
        case = os.path.join(CASES, "multibottleneck", scenario)
        edit_parking(case, scenario, message, delay, l1, l2)
        for algorithm in FORMAL:
            rows_by_family["multibottleneck"].append(row_for(
                "multibottleneck", scenario, algorithm, 1, case, 3,
                message, 80, delay * 6, "parking_lot_2link",
                "three_flow_parking_lot", "mixed"))


def raw_clos_groups(workload, message):
    n = 64
    if workload == "incast":
        return [{"stage": "incast", "step": 0, "iteration": 0,
                 "gap_ns": 0,
                 "transmissions": [(src, 63, message) for src in range(63)]}]
    spec = {"collective": workload, "participants": n,
            "message_bytes_per_rank": message, "iterations": 1}
    if workload == "all_to_all":
        return closlib.alltoall_groups(n, message, 1)
    if workload == "ring_allreduce_1d":
        return closlib.ring_groups(n, message, 1)
    if workload == "hierarchical_allreduce_2d":
        return closlib.hierarchical_groups(n, message, 1)
    if workload == "moe_all_to_all":
        groups = []
        transmissions = []
        for src in range(n):
            destinations = [((src + 1 + 8 * k) % n) for k in range(8)]
            pieces = closlib.split_bytes(message, len(destinations))
            transmissions.extend((src, dst, size)
                                 for dst, size in zip(destinations, pieces))
        groups.append({"stage": "synthetic_moe_all_to_all", "step": 0,
                       "iteration": 0, "gap_ns": 0,
                       "transmissions": transmissions})
        return groups
    raise ValueError(workload)


def materialize_clos(topology, scenario, workload, message):
    model = closlib.topology_model(topology)
    raw_groups = raw_clos_groups(workload, message)
    rng = random.Random(stable_seed("clos", scenario))
    qp_ids, qp_rounds, qp_total, paths, spines = {}, {}, {}, {}, {}
    group_rows, schedule = [], []
    for group_id, raw in enumerate(raw_groups):
        members = []
        for src, dst, size in raw["transmissions"]:
            key = (src, dst)
            if key not in qp_ids:
                fid = len(qp_ids); qp_ids[key] = fid; qp_rounds[key] = []
                qp_total[key] = 0
                spine = -1 if src // 8 == dst // 8 else rng.choice(model["spines"])
                spines[fid] = spine
                paths[fid] = closlib.fixed_path(model, src, dst, spine)
            members.append((key, int(size)))
        count = len(members)
        group_rows.append((group_id, group_id - 1, raw["gap_ns"],
                           closlib.INITIAL_RELEASE_NS if group_id == 0 else 0))
        for key, size in members:
            fid = qp_ids[key]; src, _ = key
            qp_rounds[key].append((fid, len(qp_rounds[key]), group_id, count,
                                   size, raw["gap_ns"], 0, src,
                                   closlib.INITIAL_RELEASE_NS if group_id == 0 else 0))
            qp_total[key] += size
        schedule.append({"group_id": group_id,
                         "predecessor_group_id": group_id - 1,
                         "iteration": raw["iteration"], "stage": raw["stage"],
                         "step": raw["step"], "compute_gap_ns": raw["gap_ns"],
                         "participant_count": count,
                         "total_payload_bytes": sum(x[1] for x in members)})
    flows = [None] * len(qp_ids); rounds = []
    for key, fid in qp_ids.items():
        flows[fid] = (key[0], key[1], qp_total[key]); rounds.extend(qp_rounds[key])
    return model, flows, sorted(rounds), paths, spines, group_rows, schedule


def write_clos_case(case, scenario, workload, message, oversub):
    topology = "clos_1to1_64h" if oversub == "1:1" else "clos_2to1_64h"
    model, flows, rounds, paths, spines, groups, schedule = materialize_clos(
        topology, scenario, workload, message)
    os.makedirs(case, exist_ok=True)
    switches = model["leaves"] + model["spines"]
    with open(os.path.join(case, "topology.txt"), "w") as stream:
        stream.write("%d %d %d\n" % (64 + 8 + len(model["spines"]),
                                      len(switches), len(model["physical"])))
        stream.write(" ".join(map(str, switches)) + "\n")
        for left, right in model["physical"]:
            stream.write("%d %d 100Gbps 0.001ms 0\n" % (left, right))
    with open(os.path.join(case, "flow.txt"), "w") as stream:
        stream.write("%d\n" % len(flows))
        for src, dst, total in flows:
            stream.write("%d %d 3 100 %d 0.009990000\n" % (src, dst, total))
    with open(os.path.join(case, "rounds.txt"), "w") as stream:
        stream.write("%d\n" % len(rounds))
        for item in rounds: stream.write(" ".join(map(str, item)) + "\n")
    with open(os.path.join(case, "fixed_paths.txt"), "w") as stream:
        for fid in range(len(flows)): stream.write("%d %d\n" % (fid, spines[fid]))
    with open(os.path.join(case, "multilink_links.txt"), "w") as stream:
        stream.write("%d\n" % len(model["controlled_links"]))
        for lid, node, interface, _l, _r, telemetry in model["controlled_links"]:
            stream.write("%d %d %d 100000000000 400000 0 %d\n" %
                         (lid, node, interface, int(telemetry)))
    with open(os.path.join(case, "multilink_paths.txt"), "w") as stream:
        stream.write("%d\n" % len(paths))
        for fid in range(len(paths)):
            stream.write("%d %d %s\n" %
                         (fid, len(paths[fid]), " ".join(map(str, paths[fid]))))
    with open(os.path.join(case, "group_schedule.txt"), "w") as stream:
        stream.write("%d\n" % len(groups))
        for item in groups: stream.write(" ".join(map(str, item)) + "\n")
    write_csv(os.path.join(case, "collective_schedule.csv"),
              ["group_id", "predecessor_group_id", "iteration", "stage",
               "step", "compute_gap_ns", "participant_count",
               "total_payload_bytes"], schedule)
    with open(os.path.join(case, "trace.txt"), "w") as stream: stream.write("0\n")
    with open(os.path.join(case, "config.txt"), "w") as stream:
        stream.write(old_clos_generator.base_config(1.2 if message >= (64 << 20) else .3))
    rewrite(os.path.join(case, "config.txt"), {
        "PFC_RUNTIME_ENABLE": 1, "CBAP_ENABLE": 0,
        "CBAP_LINK_FILE": "multilink_links.txt",
        "CBAP_PATH_FILE": "multilink_paths.txt", "CBAP_SCOPE_POLICY": 0,
        "CBAP_SCOPE_BASE_CC": 1, "CBAP_RATE_FLOOR_POLICY": 0,
        "CBAP_CONTROL_EPOCH_US": 5, "CBAP_PLANNING_DELAY_US": 5,
        "CBAP_CONTROL_DELAY_US": 5, "CBAP_RHO": .95,
        "CBAP_EPSILON_RATE": .02, "CBAP_PRIORITY": 3,
        "CBAP_MAX_WIRE_PACKET_BYTES": 1064, "CBAP_SUMMARY_BYTES": 64,
        "CBAP_GRANT_BYTES": 48,
    })
    dump(os.path.join(case, "scenario_meta.json"), {
        "scenario": scenario, "family": "clos", "topology": topology,
        "workload": workload, "synthetic_workload": True,
        "message_bytes_per_rank": message, "host_count": 64,
        "leaf_count": 8, "spine_count": len(model["spines"]),
        "host_link_rate_bps": 100000000000,
        "leaf_spine_rate_bps": 100000000000,
        "oversubscription": oversub, "fixed_path": True,
        "fixed_path_policy": "seeded_spine_per_five_tuple",
        "link_delay": "0.001ms", "rtt_us": 6,
        "ecn_kmin_bytes": 400000, "ecn_kmax_bytes": 1600000,
        "pfc_runtime_enabled": True, "workload_participants": 64,
        "pending_flow_ids": list(range(len(flows))), "incumbent_flow_ids": [],
        "capacity_bps": 100000000000, "expected_scope_decision": "ENABLE",
    })
    refresh_case(case)


def generate_clos(rows_by_family):
    for workload in ("incast", "all_to_all", "ring_allreduce_1d",
                     "hierarchical_allreduce_2d", "moe_all_to_all"):
        for label in ("1m", "64m"):
            for oversub in ("1:1", "2:1"):
                scenario = "clos_%s_%s_%s" % (workload, label,
                                               oversub.replace(":", "to"))
                case = os.path.join(CASES, "clos", scenario)
                write_clos_case(case, scenario, workload, MESSAGE[label], oversub)
                for algorithm in FORMAL:
                    rows_by_family["clos"].append(row_for(
                        "clos", scenario, algorithm, 1, case, 64,
                        MESSAGE[label], 0, 0,
                        "clos_64h_%s" % oversub.replace(":", "to"),
                        workload, oversub))


def generate_randomized(rows_by_family):
    specs = [(16, "256k", 80), (16, "1m", 80), (64, "256k", 80),
             (64, "1m", 80), (64, "4m", 80), (64, "1m", 95)]
    for fanin, label, load in specs:
        base = "fan%d_msg%s_load%d" % (fanin, label, load)
        hashes = []
        for seed in (1, 2, 3, 4, 5):
            scenario = "%s_random_seed%d" % (base, seed)
            rng = random.Random(stable_seed("randomized", base, seed))
            # Shift the common release by -2 us and use nonnegative jitter so
            # the actual newcomer releases cover the preregistered +/-2 us.
            offsets = {i: rng.randint(0, 4000) for i in range(fanin)}
            record = {
                "seed": seed,
                "background_phase_ns": rng.randint(0, 50000),
                "background_arrival_offset_ns": rng.randint(-50000, 50000),
                "newcomer_release_jitter_ns": {str(i): offsets[i] - 2000
                                                for i in offsets},
                "ecmp_hash_seed": rng.getrandbits(32),
            }
            case = os.path.join(CASES, "randomized", scenario)
            generate_star(case, scenario, fanin, MESSAGE[label], load,
                          offsets, record, release_base_ns=2998000)
            # Both preregistered background timing variables alter executable
            # inputs while preserving ample registration lead time.
            flow_path = os.path.join(case, "flow.txt")
            flows = [line.split() for line in open(flow_path) if line.split()]
            background_registration_ns = 400000 + record["background_arrival_offset_ns"]
            flows[1][5] = "%.9f" % (background_registration_ns * 1e-9)
            with open(flow_path, "w") as stream:
                stream.write(flows[0][0] + "\n")
                for words in flows[1:]: stream.write(" ".join(words) + "\n")
            rounds_path = os.path.join(case, "rounds.txt")
            round_rows = [line.split() for line in open(rounds_path) if line.split()]
            background_release_ns = 500000 + record["background_phase_ns"]
            round_rows[1][8] = str(background_release_ns)
            with open(rounds_path, "w") as stream:
                stream.write(round_rows[0][0] + "\n")
                for words in round_rows[1:]: stream.write(" ".join(words) + "\n")
            group_path = os.path.join(case, "group_schedule.txt")
            group_rows = [line.split() for line in open(group_path) if line.split()]
            group_rows[1][3] = str(background_release_ns)
            with open(group_path, "w") as stream:
                stream.write(group_rows[0][0] + "\n")
                for words in group_rows[1:]: stream.write(" ".join(words) + "\n")
            # Registration time safely precedes the earliest actual release.
            refresh_case(case, {"family": "randomized",
                                "randomized_base_scenario": base,
                                "random_seed_changes_input": True})
            hashes.append(sha(os.path.join(case, "random_input.json")))
            for algorithm in FORMAL:
                rows_by_family["randomized"].append(row_for(
                    "randomized", scenario, algorithm, seed, case, fanin,
                    MESSAGE[label], load, 4))
        if len(set(hashes)) != 5:
            raise RuntimeError("randomized seed did not alter input: " + base)


def find_case(family, scenario):
    path = os.path.join(CASES, family, scenario)
    if not os.path.isdir(path): raise RuntimeError("missing case " + path)
    return path


def generate_ablations(rows_by_family):
    reps = [
        ("single_bottleneck", "fan4_msg64k_load80"),
        ("single_bottleneck", "fan16_msg256k_load80"),
        ("single_bottleneck", "fan32_msg1m_load80"),
        ("single_bottleneck", "fan64_msg256k_load80"),
        ("single_bottleneck", "fan64_msg1m_load80"),
        ("single_bottleneck", "fan64_msg4m_load80"),
        ("single_bottleneck", "fan64_msg1m_load95"),
        ("multibottleneck", "parking_sync_1m_load80"),
    ]
    for family, scenario in reps:
        case = find_case(family, scenario)
        meta = json.load(open(os.path.join(case, "scenario_meta.json")))
        for algorithm in ("cbap_init_only", "cbap_rateonly_v11"):
            rows_by_family["ablation"].append(row_for(
                "ablation", scenario, algorithm, 1, case,
                meta.get("pending_count", len(meta.get("pending_flow_ids", []))),
                meta.get("message_bytes", ""),
                meta.get("incumbent_offered_load_percent", 80), 0,
                meta.get("topology", "star_100g"),
                meta.get("workload", "synchronous_incast")))
    for scenario in ("fan64_msg1m_load80", "fan64_msg4m_load80",
                     "fan64_msg1m_load95"):
        case = find_case("single_bottleneck", scenario)
        meta = json.load(open(os.path.join(case, "scenario_meta.json")))
        for algorithm in ("cbap_full_v14_stable_handoff",
                          "cbap_full_v15_guarded_delegation"):
            rows_by_family["ablation"].append(row_for(
                "ablation", scenario, algorithm, 1, case,
                meta["pending_count"], meta["message_bytes"],
                meta["incumbent_offered_load_percent"], 0))


def write_manifests(rows_by_family):
    names = {
        "single_bottleneck": "single_bottleneck.csv",
        "release_skew": "release_skew.csv",
        "multibottleneck": "multibottleneck.csv", "clos": "clos.csv",
        "randomized": "randomized_robustness.csv", "ablation": "ablations.csv",
    }
    all_rows = []
    for family, name in names.items():
        write_csv(os.path.join(MANIFESTS, name), FIELDS, rows_by_family[family])
        all_rows.extend(rows_by_family[family])
    write_csv(os.path.join(MANIFESTS, "all_runs.csv"), FIELDS, all_rows)
    # Preflight is a seven-algorithm sample and is intentionally outside 1408.
    source = find_case("single_bottleneck", "fan16_msg256k_load80")
    preflight = [row_for("preflight", "fan16_msg256k_load80", algorithm,
                         1, source, 16, MESSAGE["256k"], 80, 0)
                 for algorithm in FORMAL]
    write_csv(os.path.join(MANIFESTS, "preflight.csv"), FIELDS, preflight)
    expected = {"single_bottleneck": 560, "release_skew": 420,
                "multibottleneck": 56, "clos": 140,
                "randomized": 210, "ablation": 22}
    actual = {key: len(rows_by_family[key]) for key in expected}
    if actual != expected or len(all_rows) != 1408:
        raise RuntimeError("manifest count mismatch %r total=%d" %
                           (actual, len(all_rows)))
    dump(os.path.join(MANIFESTS, "manifest_counts.json"),
         {"families": actual, "total": len(all_rows), "preflight": 7})
    return actual


def main():
    gate = os.path.join(REPO, "cbap_final_metric_pipeline", "reports",
                        "metric_pipeline_selftest.md")
    if not os.path.isfile(gate) or "METRIC_PIPELINE_PASS" not in open(gate).read():
        raise SystemExit("METRIC_PIPELINE_BLOCKED")
    os.makedirs(CASES, exist_ok=True); os.makedirs(MANIFESTS, exist_ok=True)
    rows = {name: [] for name in ("single_bottleneck", "release_skew",
                                  "multibottleneck", "clos", "randomized",
                                  "ablation")}
    generate_single_and_skew(rows)
    generate_multibottleneck(rows)
    generate_clos(rows)
    generate_randomized(rows)
    generate_ablations(rows)
    counts = write_manifests(rows)
    print("METRIC_PIPELINE_PASS")
    print(" ".join("%s=%d" % item for item in counts.items()))
    print("total=1408 preflight=7")


if __name__ == "__main__":
    main()
