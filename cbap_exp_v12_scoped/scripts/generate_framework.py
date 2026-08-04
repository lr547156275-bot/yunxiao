#!/usr/bin/env python3
"""Generate deterministic CBAP-v1.2 scope/core inputs; never runs ns-3."""
import csv, hashlib, json, os, shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(ROOT, ".."))
TEMPLATE = os.path.join(REPO, "cbap_exp_v11_freeze", "cases",
                        "e2_batch_incast", "default", "config.txt")
V11 = os.path.join(REPO, "cbap_exp_v11_freeze", "cases")

ALGOS = {
    "dctcp": (8, False, "baseline", "ALWAYS"),
    "dcqcn": (1, False, "baseline", "ALWAYS"),
    "timely": (7, False, "baseline", "ALWAYS"),
    "hpcc_int": (3, False, "baseline", "ALWAYS"),
    "bop_qb": (15, False, "bop_qb_v1", "ALWAYS"),
    "independent_min_grant": (20, True, "v1", "ALWAYS"),
    "cbap_init_only": (21, True, "v1.1", "ALWAYS"),
    "cbap_rateonly_v11": (22, True, "v1.1", "ALWAYS"),
    "cbap_full_v11_unscoped": (23, True, "v1.1", "ALWAYS"),
    "cbap_full_v12_scoped": (24, True, "v1.2", "SHARED_BATCH_OVERSUBSCRIPTION"),
}

def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def rewrite(path, updates):
    lines, seen = [], set()
    for line in open(path):
        words = line.split(); key = words[0] if words else ""
        if key in updates:
            lines.append("%s %s\n" % (key, updates[key])); seen.add(key)
        else:
            lines.append(line)
    for key in sorted(set(updates) - seen):
        lines.append("%s %s\n" % (key, updates[key]))
    with open(path, "w") as f: f.writelines(lines)

def finish_case(path, meta, switch, bottleneck_if, flow_count):
    shutil.copy2(TEMPLATE, os.path.join(path, "config.txt"))
    selected = ",".join(str(i) for i in range(min(4, flow_count))) or "0"
    rewrite(os.path.join(path, "config.txt"), {
        "SIMULATOR_STOP_TIME": "0.10", "ROUND_TRACE_SELECTED_FLOWS": selected,
        "ROUND_TRACE_SELECTED_LINKS": "%d:%d" % (switch, bottleneck_if),
        "KMAX_MAP": "6 10000000000 1600 50000000000 1600 80000000000 1600 95000000000 1600 100000000000 1600 400000000000 1600",
        "KMIN_MAP": "6 10000000000 400 50000000000 400 80000000000 400 95000000000 400 100000000000 400 400000000000 400",
        "PMAX_MAP": "6 10000000000 0.2 50000000000 0.2 80000000000 0.2 95000000000 0.2 100000000000 0.2 400000000000 0.2",
        "CBAP_SCOPE_POLICY": 0, "CBAP_SCOPE_BASE_CC": 1,
        "CBAP_SCOPE_SUMMARY_FILE": "scope_summary.csv",
        "CBAP_SCOPE_LINK_FILE": "scope_link_summary.csv",
    })
    with open(os.path.join(path, "scenario_meta.json"), "w") as f:
        json.dump(meta, f, indent=2, sort_keys=True); f.write("\n")
    names = ("topology.txt", "flow.txt", "rounds.txt", "fixed_paths.txt",
             "controlled_links.txt", "controlled_paths.txt",
             "group_schedule.txt", "trace.txt")
    with open(os.path.join(path, "input_hashes.json"), "w") as f:
        json.dump({n: digest(os.path.join(path, n)) for n in names}, f,
                  indent=2, sort_keys=True); f.write("\n")

def star_case(root, name, pending, message, load=0, delay_us=1,
              pending_access=100, expected="ENABLE"):
    path = os.path.join(root, name); os.makedirs(path, exist_ok=True)
    incumbent_count = 1 if load else 0
    senders = incumbent_count + pending
    receiver, switch = senders, senders + 1
    with open(os.path.join(path, "topology.txt"), "w") as f:
        f.write("%d 1 %d\n%d\n" % (senders + 2, senders + 1, switch))
        for node in range(senders):
            rate = load if node < incumbent_count else pending_access
            f.write("%d %d %gGbps 0.%03dms 0\n" %
                    (node, switch, rate, delay_us))
        f.write("%d %d 100Gbps 0.%03dms 0\n" %
                (receiver, switch, delay_us))
    incumbent_size = 512 * 1024 * 1024
    with open(os.path.join(path, "flow.txt"), "w") as f:
        f.write("%d\n" % senders)
        if incumbent_count:
            f.write("0 %d 3 100 %d 0.000490000\n" %
                    (receiver, incumbent_size))
        for i in range(pending):
            flow = incumbent_count + i
            f.write("%d %d 3 100 %d 0.002990000\n" %
                    (flow, receiver, message))
    with open(os.path.join(path, "rounds.txt"), "w") as f:
        f.write("%d\n" % senders)
        group = 0
        if incumbent_count:
            f.write("0 0 0 1 %d 0 0 0 500000\n" % incumbent_size)
            group = 1
        for i in range(pending):
            flow = incumbent_count + i
            f.write("%d 0 %d %d %d 0 0 %d 3000000\n" %
                    (flow, group, pending, message, i))
    with open(os.path.join(path, "group_schedule.txt"), "w") as f:
        f.write("%d\n" % (1 + incumbent_count))
        if incumbent_count: f.write("0 -1 0 500000\n1 -1 0 3000000\n")
        else: f.write("0 -1 0 3000000\n")
    with open(os.path.join(path, "fixed_paths.txt"), "w") as f:
        for i in range(senders): f.write("%d -1\n" % i)
    with open(os.path.join(path, "controlled_links.txt"), "w") as f:
        f.write("1\n1 %d %d 100000000000 400000 0 1\n" %
                (switch, senders + 1))
    with open(os.path.join(path, "controlled_paths.txt"), "w") as f:
        f.write("%d\n" % senders)
        for i in range(senders): f.write("%d 1 1\n" % i)
    open(os.path.join(path, "trace.txt"), "w").write("0\n")
    meta = {"scenario": name, "pending_count": pending,
            "message_bytes": message, "incumbent_offered_load_percent": load,
            "expected_scope_decision": expected, "fixed_path": True,
            "common_release_ns": 3000000, "capacity_bps": 100000000000,
            "application_ready_to_network_release_ns": 5000,
            "pending_flow_ids": list(range(incumbent_count, senders)),
            "incumbent_flow_ids": list(range(incumbent_count))}
    finish_case(path, meta, switch, senders + 1, senders)

def no_shared_case(root):
    name = "no_shared_link"; path = os.path.join(root, name)
    os.makedirs(path, exist_ok=True); count = 8
    # sender[0..7], receiver[8..15], switch 16; eight distinct egresses.
    switch = 16
    with open(os.path.join(path, "topology.txt"), "w") as f:
        f.write("17 1 16\n16\n")
        for i in range(8): f.write("%d 16 100Gbps 0.001ms 0\n" % i)
        for i in range(8, 16): f.write("%d 16 100Gbps 0.001ms 0\n" % i)
    with open(os.path.join(path, "flow.txt"), "w") as f:
        f.write("8\n")
        for i in range(8): f.write("%d %d 3 100 1048576 0.002990000\n" % (i, i+8))
    with open(os.path.join(path, "rounds.txt"), "w") as f:
        f.write("8\n")
        for i in range(8): f.write("%d 0 0 8 1048576 0 0 %d 3000000\n" % (i, i))
    open(os.path.join(path, "group_schedule.txt"), "w").write("1\n0 -1 0 3000000\n")
    with open(os.path.join(path, "fixed_paths.txt"), "w") as f:
        for i in range(8): f.write("%d -1\n" % i)
    with open(os.path.join(path, "controlled_links.txt"), "w") as f:
        f.write("8\n")
        for i in range(8): f.write("%d 16 %d 100000000000 400000 0 1\n" % (i+1, i+9))
    with open(os.path.join(path, "controlled_paths.txt"), "w") as f:
        f.write("8\n")
        for i in range(8): f.write("%d 1 %d\n" % (i, i+1))
    open(os.path.join(path, "trace.txt"), "w").write("0\n")
    finish_case(path, {"scenario": name, "pending_count": 8,
        "message_bytes": 1048576, "incumbent_offered_load_percent": 0,
        "expected_scope_decision": "BYPASS", "fixed_path": True,
        "common_release_ns": 3000000, "capacity_bps": 100000000000,
        "distinct_egress_links": 8, "pending_flow_ids": list(range(8)),
        "incumbent_flow_ids": []}, switch, 9, 8)

def copy_parking(scope_root):
    src = os.path.join(V11, "e4_parking_lot", "synchronous")
    dst = os.path.join(scope_root, "synchronous_parking_lot")
    if os.path.isdir(dst): shutil.rmtree(dst)
    shutil.copytree(src, dst)
    topology=os.path.join(dst,"topology.txt")
    text=open(topology).read().replace("0.001ms","0.020ms")
    open(topology,"w").write(text)
    meta = json.load(open(os.path.join(dst, "scenario_meta.json")))
    meta.update(scenario="synchronous_parking_lot",
                expected_scope_decision="ENABLE", pending_count=3,
                incumbent_offered_load_percent=0)
    with open(os.path.join(dst, "scenario_meta.json"), "w") as f:
        json.dump(meta, f, indent=2, sort_keys=True); f.write("\n")
    rewrite(os.path.join(dst, "config.txt"), {
        "LINK_DELAY": "0.020ms",
        "CBAP_SCOPE_POLICY": 0, "CBAP_SCOPE_BASE_CC": 1,
        "CBAP_SCOPE_SUMMARY_FILE": "scope_summary.csv",
        "CBAP_SCOPE_LINK_FILE": "scope_link_summary.csv"})

def copy_batch(scope_root):
    src=os.path.join(V11,"e2_batch_incast","default")
    dst=os.path.join(scope_root,"batch_incast")
    if os.path.isdir(dst):shutil.rmtree(dst)
    shutil.copytree(src,dst)
    meta=json.load(open(os.path.join(dst,"scenario_meta.json")))
    meta.update(scenario="batch_incast",expected_scope_decision="ENABLE",
                pending_count=8,incumbent_offered_load_percent=100,
                pending_flow_ids=list(range(4,12)),incumbent_flow_ids=list(range(4)))
    with open(os.path.join(dst,"scenario_meta.json"),"w") as f:json.dump(meta,f,indent=2,sort_keys=True);f.write("\n")
    rewrite(os.path.join(dst,"config.txt"),{"CBAP_SCOPE_POLICY":0,
        "CBAP_SCOPE_BASE_CC":1,"CBAP_SCOPE_SUMMARY_FILE":"scope_summary.csv",
        "CBAP_SCOPE_LINK_FILE":"scope_link_summary.csv"})

def manifests():
    os.makedirs(os.path.join(ROOT, "configs"), exist_ok=True)
    scope_scenarios = [("single_pending", "BYPASS"),
        ("batch_incast", "ENABLE"), ("two_pending_overload", "ENABLE"),
        ("two_pending_low_demand", "BYPASS"),
        ("no_shared_link", "BYPASS"),
        ("synchronous_parking_lot", "ENABLE")]
    scope_algos = ("dcqcn", "cbap_full_v11_unscoped", "cbap_full_v12_scoped")
    scope = []
    for scenario, expected in scope_scenarios:
        for algorithm in scope_algos:
            mode, _, version, policy = ALGOS[algorithm]
            scope.append({"run_id": "%s__%s__seed1" % (scenario, algorithm),
                "scenario": scenario, "algorithm_name": algorithm,
                "cc_mode": mode, "cbap_version": version,
                "scope_policy": policy, "expected_scope_decision": expected,
                "seed": 1})
    fields = list(scope[0])
    with open(os.path.join(ROOT, "configs", "scope_manifest.csv"), "w", newline="") as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(scope)

    formal = ("dctcp", "dcqcn", "timely", "hpcc_int", "bop_qb",
              "independent_min_grant", "cbap_full_v12_scoped")
    core_scenarios=[]
    for fan in (4,8,16,32,64):
        for label, size in (("64k",65536),("256k",262144),
                            ("1m",1048576),("4m",4194304)):
            core_scenarios.append(("fan%d_msg%s_load80"%(fan,label),fan,size,80))
    for load in (0,50,95): core_scenarios.append(("fan16_msg1m_load%d"%load,16,1048576,load))
    rows=[]
    for scenario, fan, size, load in core_scenarios:
        for algorithm in formal:
            mode, _, version, policy=ALGOS[algorithm]
            rows.append({"run_id":"%s__%s__seed1"%(scenario,algorithm),
                "scenario":scenario,"algorithm_name":algorithm,"cc_mode":mode,
                "cbap_version":version,"scope_policy":policy,"seed":1,
                "fan_in":fan,"message_bytes":size,"incumbent_load_percent":load,
                "ablation":0})
    representatives=("fan4_msg64k_load80","fan16_msg1m_load80","fan64_msg4m_load80")
    for scenario in representatives:
        fan=int(scenario.split("_")[0][3:]); size={"64k":65536,"1m":1048576,"4m":4194304}[scenario.split("_")[1][3:]]
        for algorithm in ("cbap_init_only","cbap_rateonly_v11","cbap_full_v11_unscoped"):
            mode,_,version,policy=ALGOS[algorithm]
            rows.append({"run_id":"%s__%s__seed1"%(scenario,algorithm),
                "scenario":scenario,"algorithm_name":algorithm,"cc_mode":mode,
                "cbap_version":version,"scope_policy":policy,"seed":1,
                "fan_in":fan,"message_bytes":size,"incumbent_load_percent":80,
                "ablation":1})
    fields=list(rows[0])
    with open(os.path.join(ROOT,"configs","core_manifest.csv"),"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def main():
    scope=os.path.join(ROOT,"cases","scope")
    core=os.path.join(ROOT,"cases","core")
    os.makedirs(scope,exist_ok=True);os.makedirs(core,exist_ok=True)
    star_case(scope,"single_pending",1,2*1024*1024,80,expected="BYPASS")
    copy_batch(scope)
    star_case(scope,"two_pending_overload",2,1024*1024,0,20,100,"ENABLE")
    star_case(scope,"two_pending_low_demand",2,1024*1024,0,1,10,"BYPASS")
    no_shared_case(scope); copy_parking(scope)
    for fan in (4,8,16,32,64):
        for label,size in (("64k",65536),("256k",262144),("1m",1048576),("4m",4194304)):
            star_case(core,"fan%d_msg%s_load80"%(fan,label),fan,size,80)
    for load in (0,50,95):
        star_case(core,"fan16_msg1m_load%d"%load,16,1048576,load)
    manifests()
    print("scope_runs=18 core_runs=170")

if __name__ == "__main__": main()
