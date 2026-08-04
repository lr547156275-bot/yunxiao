#!/usr/bin/env python3
import csv
import hashlib
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CASES = os.path.join(ROOT, "cases")
CONFIG = os.path.join(ROOT, "config")

MIB = 1024 * 1024
ALGORITHMS = {
    "dcqcn": 1,
    "hpcc_int": 3,
    "bop_qb": 15,
    "independent_min_grant": 20,
    "cbap_init_only": 21,
    "cbap_rate_only": 22,
    "cbap_full": 23,
}


def link(a, b, rate="100Gbps", delay="0.001ms"):
    return (a, b, rate, delay, 0)


def interface_map(links):
    count, result = {}, {}
    for a, b, _, _, _ in links:
        count[a] = count.get(a, 0) + 1
        count[b] = count.get(b, 0) + 1
        result[(a, b)] = count[a]
        result[(b, a)] = count[b]
    return result


def base_config(stop, pfc, selected):
    return {
        "ENABLE_QCN": 1,
        "PFC_RUNTIME_ENABLE": pfc,
        "USE_DYNAMIC_PFC_THRESHOLD": 1,
        "CLAMP_TARGET_RATE": 0,
        "PAUSE_TIME": 5,
        "DATA_RATE": "100Gbps",
        "LINK_DELAY": "0.001ms",
        "PACKET_PAYLOAD_SIZE": 1000,
        "L2_CHUNK_SIZE": 4000,
        "L2_ACK_INTERVAL": 1,
        "L2_BACK_TO_ZERO": 0,
        "TOPOLOGY_FILE": "topology.txt",
        "FLOW_FILE": "flow.txt",
        "FIXED_PATH_FILE": "fixed_paths.txt",
        "FIXED_PATH_OUTPUT_FILE": "resolved_fixed_paths.csv",
        "TRACE_FILE": "trace.txt",
        "TRACE_OUTPUT_FILE": "/dev/null",
        "SIMULATOR_STOP_TIME": stop,
        "CC_MODE": 1,
        "SIM_SEED": 1,
        "ALPHA_RESUME_INTERVAL": 55,
        "RATE_DECREASE_INTERVAL": 4,
        "RP_TIMER": 300,
        "EWMA_GAIN": 0.00390625,
        "FAST_RECOVERY_TIMES": 5,
        "RATE_AI": "50Mb/s",
        "RATE_HAI": "100Mb/s",
        "MIN_RATE": "100Mb/s",
        "DCTCP_RATE_AI": "1000Mb/s",
        "ERROR_RATE_PER_LINK": 0,
        "HAS_WIN": 1,
        "GLOBAL_T": 1,
        "MI_THRESH": 5,
        "VAR_WIN": 0,
        "FAST_REACT": 1,
        "U_TARGET": 0.95,
        "INT_MULTI": 1,
        "RATE_BOUND": 1,
        "ACK_HIGH_PRIO": 0,
        "LINK_DOWN": "0 0 0",
        "ENABLE_TRACE": 0,
        "BUFFER_SIZE": 32,
        "QLEN_MON_FILE": "/dev/null",
        "QLEN_MON_START": 1000000000,
        "QLEN_MON_END": 1000000001,
        "KMAX_MAP": "3 50000000000 1600 100000000000 1600 "
                    "400000000000 1600",
        "KMIN_MAP": "3 50000000000 400 100000000000 400 "
                    "400000000000 400",
        "PMAX_MAP": "3 50000000000 0.2 100000000000 0.2 "
                    "400000000000 0.2",
        "MULTI_RATE": 1,
        "SAMPLE_FEEDBACK": 0,
        "ROUND_SCHEDULE_FILE": "rounds.txt",
        "ROUND_MODE": 1,
        "ROUND_TRACE_SELECTED_FLOWS": "0,1,2,3",
        "ROUND_TRACE_SELECTED_LINKS": selected,
        "CRFM_TRACE_SAMPLE_US": 10,
        "CRFM_MAX_TRACE_FILE_MB": 64,
        "CRFM_MAX_TRACE_TOTAL_MB": 128,
        "CRFM_MIN_FREE_GB": 5,
        "CRFM_MAX_EVENT_ROWS": 200000,
        "CRFM_DEBUG": 0,
        "BOP_RHO": 1.0,
        "BOP_BACKGROUND_BPS": 0,
        "BOP_PHASE_STAGGER": 0,
        "BOP_PACKET_BYTES": 1064,
        "BOP_BOTTLENECK_BPS": 100000000000,
        "BOP_MULTILINK_ENABLE": 1,
        "BOP_MULTILINK_LINK_FILE": "controlled_links.txt",
        "BOP_MULTILINK_PATH_FILE": "controlled_paths.txt",
        "BOP_MULTILINK_GROUP_FILE": "group_schedule.txt",
        "BOP_QB_QUEUE_FRACTION": 0.50,
        "BOP_QB_PACKET_MARGIN": 1,
        "BOP_QB_ENABLE_PHASE_STAGGER": 0,
        "CBAP_ENABLE": 0,
        "CBAP_LINK_FILE": "controlled_links.txt",
        "CBAP_PATH_FILE": "controlled_paths.txt",
        "CBAP_CONTROL_EPOCH_US": 5,
        "CBAP_PLANNING_DELAY_US": 5,
        "CBAP_CONTROL_DELAY_US": 5,
        "CBAP_RHO": 0.95,
        "CBAP_EPSILON_RATE": 0.02,
        "CBAP_PRIORITY": 3,
        "CBAP_MAX_WIRE_PACKET_BYTES": 1064,
        "CBAP_SUMMARY_BYTES": 64,
        "CBAP_GRANT_BYTES": 48,
        "FLOW_SUMMARY_FILE": "flow_summary.csv",
        "ROUND_SUMMARY_FILE": "round_summary.csv",
        "FEEDBACK_SUMMARY_FILE": "feedback_summary.csv",
        "CONTROLLER_SUMMARY_FILE": "controller_summary.csv",
        "GROUP_ROUND_SUMMARY_FILE": "group_round_summary.csv",
        "FLOW_PLAN_FILE": "flow_plan.csv",
        "LINK_TIMESERIES_FILE": "selected_link_timeseries.csv",
        "SELECTED_FLOW_TIMESERIES_FILE": "selected_flow_timeseries.csv",
        "PFC_OUTPUT_FILE": "pfc_events.csv",
        "BOP_QB_GROUP_DECISIONS_FILE": "bop_qb_group_decisions.csv",
        "BOP_MULTILINK_GROUP_DECISIONS_FILE":
            "bop_multilink_group_decisions.csv",
        "BOP_MULTILINK_LINK_CONSTRAINTS_FILE":
            "bop_multilink_link_constraints.csv",
        "CBAP_PORT_SUMMARY_FILE": "cbap_port_summary.csv",
        "CBAP_ADMISSION_FILE": "cbap_admission.csv",
        "CBAP_RATE_TRANSITION_FILE": "cbap_rate_transitions.csv",
        "CBAP_FLOW_STATE_FILE": "cbap_flow_state.csv",
        "CBAP_CONTROL_OVERHEAD_FILE": "cbap_control_overhead.csv",
        "FCT_OUTPUT_FILE": "/dev/null",
        "ALGORITHM": "dcqcn",
        "SCENARIO": "unset",
        "FINAL_VALIDATION_ENABLE": 0,
    }


def write_case(scenario, subcase, node_count, switches, links, flows,
               rounds, controlled, paths, groups, stop, pfc=1,
               metadata=None):
    case = os.path.join(CASES, scenario, subcase)
    os.makedirs(case, exist_ok=True)
    ifmap = interface_map(links)
    resolved = []
    for item in controlled:
        link_id, src, dst, capacity, ecn, background = item
        resolved.append((link_id, src, ifmap[(src, dst)], capacity,
                         ecn, background, 1))
    with open(os.path.join(case, "topology.txt"), "w") as out:
        out.write("%d %d %d\n" % (node_count, len(switches), len(links)))
        out.write(" ".join(str(x) for x in switches) + "\n")
        for row in links:
            out.write("%d %d %s %s %d\n" % row)
    with open(os.path.join(case, "flow.txt"), "w") as out:
        out.write("%d\n" % len(flows))
        for src, dst, size, ready in flows:
            out.write("%d %d 3 100 %d %.9f\n" %
                      (src, dst, size, ready - 0.000010))
    with open(os.path.join(case, "rounds.txt"), "w") as out:
        out.write("%d\n" % len(rounds))
        for row in rounds:
            out.write("%d %d %d %d %d %d %d %d %d\n" % row)
    with open(os.path.join(case, "fixed_paths.txt"), "w") as out:
        for flow_id in range(len(flows)):
            out.write("%d -1\n" % flow_id)
    with open(os.path.join(case, "controlled_links.txt"), "w") as out:
        out.write("%d\n" % len(resolved))
        for row in resolved:
            out.write("%d %d %d %d %d %d %d\n" % row)
    with open(os.path.join(case, "controlled_paths.txt"), "w") as out:
        out.write("%d\n" % len(paths))
        for flow_id in range(len(paths)):
            path = paths[flow_id]
            out.write("%d %d %s\n" %
                      (flow_id, len(path), " ".join(map(str, path))))
    with open(os.path.join(case, "group_schedule.txt"), "w") as out:
        out.write("%d\n" % len(groups))
        for group_id, release_ns in sorted(groups.items()):
            out.write("%d -1 0 %d\n" % (group_id, release_ns))
    with open(os.path.join(case, "trace.txt"), "w") as out:
        out.write("0\n")
    selected = ",".join("%d:%d" % (row[1], row[2]) for row in resolved)
    config = base_config(stop, pfc, selected)
    config["SCENARIO"] = scenario
    with open(os.path.join(case, "config.txt"), "w") as out:
        for key, value in config.items():
            out.write("%s %s\n" % (key, value))
    meta = {
        "scenario": scenario,
        "subcase": subcase,
        "fixed_path": True,
        "global_barrier": True,
        "packet_payload_bytes": 1000,
        "ecn_kmin_bytes": 400000,
        "ecn_kmax_bytes": 1600000,
        "pfc_runtime_enabled": bool(pfc),
        "controlled_links": [
            {"link_id": row[0], "node": row[1], "if_index": row[2],
             "capacity_bps": row[3], "ecn_threshold_bytes": row[4]}
            for row in resolved
        ],
        "application_ready_times_s": [f[3] for f in flows],
        "flow_sizes_bytes": [f[2] for f in flows],
    }
    if metadata:
        meta.update(metadata)
    with open(os.path.join(case, "scenario_meta.json"), "w") as out:
        json.dump(meta, out, indent=2, sort_keys=True)
        out.write("\n")
    hashes = {}
    for name in ("topology.txt", "flow.txt", "rounds.txt",
                 "fixed_paths.txt", "controlled_links.txt",
                 "controlled_paths.txt", "group_schedule.txt"):
        data = open(os.path.join(case, name), "rb").read()
        hashes[name] = hashlib.sha256(data).hexdigest()
    with open(os.path.join(case, "input_hashes.json"), "w") as out:
        json.dump(hashes, out, indent=2, sort_keys=True)
        out.write("\n")


def one_switch_case(scenario, subcase, flows, group_for_flow, stop,
                    pfc=1, metadata=None):
    receiver = max(f[0] for f in flows) + 1
    switch = receiver + 1
    links = [link(f[0], switch) for f in flows]
    links.append(link(receiver, switch))
    ready_by_group = {}
    membership = {}
    for flow_id, (_, _, _, ready) in enumerate(flows):
        group = group_for_flow[flow_id]
        ready_by_group[group] = int(round(ready * 1e9))
        membership[group] = membership.get(group, 0) + 1
    rounds = []
    rank = {}
    for flow_id, (_, _, size, _) in enumerate(flows):
        group = group_for_flow[flow_id]
        sender_rank = rank.get(group, 0)
        rank[group] = sender_rank + 1
        rounds.append((flow_id, 0, group, membership[group], size,
                       0, 0, sender_rank, ready_by_group[group]))
    controlled = [(1, switch, receiver, 100000000000, 400000, 0)]
    paths = {flow_id: [1] for flow_id in range(len(flows))}
    write_case(scenario, subcase, switch + 1, [switch], links, flows,
               rounds, controlled, paths, ready_by_group, stop, pfc,
               metadata)


def generate():
    os.makedirs(CONFIG, exist_ok=True)
    # E1
    one_switch_case(
        "e1_single_old_single_new", "default",
        [(0, 2, 128 * MIB, 0.0005), (1, 2, 4 * MIB, 0.0030)],
        {0: 0, 1: 1}, 0.030,
        metadata={"old_flow_ids": [0], "new_flow_ids": [1]})
    # E2
    flows = [(i, 12, 128 * MIB, 0.0005) for i in range(4)]
    flows += [(i, 12, 4 * MIB, 0.0030) for i in range(4, 12)]
    groups = dict((i, 0 if i < 4 else 1) for i in range(12))
    one_switch_case(
        "e2_batch_incast", "default", flows, groups, 0.080,
        metadata={"old_flow_ids": list(range(4)),
                  "new_flow_ids": list(range(4, 12))})
    # E3
    switches = [7, 8]
    links = [link(i, 7, "50Gbps") for i in range(4)]
    links += [link(4, 7), link(7, 8, "400Gbps"),
              link(8, 5), link(8, 6)]
    ifmap = interface_map(links)
    controlled = [
        (1, 7, 8, 400000000000, 400000, 0),
        (2, 8, 5, 100000000000, 400000, 0),
        (3, 8, 6, 100000000000, 400000, 0),
    ]
    victim = [(4, 6, 128 * MIB, 0.0005)]
    victim_round = [(0, 0, 0, 1, 128 * MIB, 0, 0, 0, 500000)]
    write_case("e3_victim_flow", "victim_alone", 9, switches, links,
               victim, victim_round, controlled, {0: [1, 3]},
               {0: 500000}, 0.030, 1,
               {"victim_flow_id": 0, "true_root_link_id": 2})
    vf = victim + [(i, 5, 8 * MIB, 0.0030) for i in range(4)]
    vr = [(0, 0, 0, 1, 128 * MIB, 0, 0, 0, 500000)]
    for i in range(1, 5):
        vr.append((i, 0, 1, 4, 8 * MIB, 0, 0, i - 1, 3000000))
    vp = {0: [1, 3]}
    for i in range(1, 5):
        vp[i] = [1, 2]
    for subcase, pfc in (("pfc_on", 1), ("pfc_off", 0)):
        write_case("e3_victim_flow", subcase, 9, switches, links, vf, vr,
                   controlled, vp, {0: 500000, 1: 3000000}, 0.030,
                   pfc, {"victim_flow_id": 0,
                         "contributor_flow_ids": [1, 2, 3, 4],
                         "true_root_link_id": 2,
                         "shared_upstream_link_id": 1})
    # E4
    switches = [6, 7, 8]
    links = [link(0, 6), link(1, 6), link(6, 7), link(3, 7),
             link(2, 7), link(7, 8), link(4, 8), link(5, 8)]
    controlled = [
        (1, 6, 7, 100000000000, 400000, 0),
        (2, 7, 8, 100000000000, 400000, 0),
    ]
    paths = {0: [1, 2], 1: [1], 2: [2]}
    sync_flows = [(1, 4, 64 * MIB, 0.0030),
                  (0, 3, 64 * MIB, 0.0030),
                  (2, 5, 64 * MIB, 0.0030)]
    sync_rounds = [(i, 0, 0, 3, 64 * MIB, 0, 0, i, 3000000)
                   for i in range(3)]
    write_case("e4_parking_lot", "synchronous", 9, switches, links,
               sync_flows, sync_rounds, controlled, paths, {0: 3000000},
               0.030, 1, {"flow_roles": {"0": "F0", "1": "F1",
                                          "2": "F2"}})
    # flow.txt is consumed in nondecreasing start-time order by third.cc.
    # Preserve the conceptual F0/F1/F2 roles while assigning old F1/F2 the
    # first two input IDs and the later F0 arrival ID 2.
    staggered_flows = [(0, 3, 128 * MIB, 0.0005),
                       (2, 5, 128 * MIB, 0.0005),
                       (1, 4, 32 * MIB, 0.0030)]
    staggered_rounds = [
        (0, 0, 0, 2, 128 * MIB, 0, 0, 0, 500000),
        (1, 0, 0, 2, 128 * MIB, 0, 0, 1, 500000),
        (2, 0, 1, 1, 32 * MIB, 0, 0, 0, 3000000),
    ]
    staggered_paths = {0: [1], 1: [2], 2: [1, 2]}
    write_case("e4_parking_lot", "staggered", 9, switches, links,
               staggered_flows, staggered_rounds, controlled,
               staggered_paths,
               {0: 500000, 1: 3000000}, 0.040, 1,
               {"flow_roles": {"0": "F1", "1": "F2", "2": "F0"}})
    manifest_path = os.path.join(CONFIG, "run_manifest.csv")
    with open(manifest_path, "w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=[
            "run_id", "scenario", "subcase", "algorithm", "cc_mode",
            "seed", "formal"])
        writer.writeheader()
        for scenario, subcase in (
            ("e1_single_old_single_new", "default"),
            ("e2_batch_incast", "default"),
            ("e3_victim_flow", "victim_alone"),
            ("e3_victim_flow", "pfc_on"),
            ("e3_victim_flow", "pfc_off"),
            ("e4_parking_lot", "synchronous"),
            ("e4_parking_lot", "staggered"),
        ):
            for algorithm, mode in ALGORITHMS.items():
                for seed in (1, 2, 3):
                    run_id = "%s__%s__%s__seed%d" % (
                        scenario, subcase, algorithm, seed)
                    writer.writerow({
                        "run_id": run_id, "scenario": scenario,
                        "subcase": subcase, "algorithm": algorithm,
                        "cc_mode": mode, "seed": seed, "formal": 1,
                    })


if __name__ == "__main__":
    generate()
