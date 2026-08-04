#!/usr/bin/env python3
"""Generate immutable CBAP-v1.1 manifests and victim calibration inputs."""
import csv
import hashlib
import json
import os
import shutil


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(ROOT, ".."))
V1 = os.path.join(REPO, "cbap_exp_v1_fix")
OLD = os.path.join(REPO, "cbap_exp")

IDENTITIES = {
    "dcqcn": (1, "baseline", "none"),
    "hpcc_int": (3, "baseline", "none"),
    "independent_min_grant": (20, "v1", "legacy_min"),
    "cbap_rateonly_v1": (22, "v1", "legacy_min"),
    "cbap_full_v1": (23, "v1", "legacy_min"),
    "cbap_rateonly_v11": (22, "v1.1", "adaptive_max"),
    "cbap_full_v11": (23, "v1.1", "adaptive_max"),
}
INPUTS = ("topology.txt", "flow.txt", "rounds.txt", "fixed_paths.txt",
          "controlled_links.txt", "controlled_paths.txt", "group_schedule.txt",
          "trace.txt", "scenario_meta.json", "input_hashes.json",
          "input_hashes_v1.json")


def sha(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rewrite(path, updates):
    lines, seen = [], set()
    for line in open(path):
        key = line.split()[0] if line.split() else ""
        if key in updates:
            lines.append("%s %s\n" % (key, updates[key])); seen.add(key)
        else:
            lines.append(line)
    for key in sorted(set(updates) - seen):
        lines.append("%s %s\n" % (key, updates[key]))
    with open(path, "w") as stream:
        stream.writelines(lines)


def copy_main_cases():
    cases = (("e1_single_old_single_new", "default"),
             ("e2_batch_incast", "default"),
             ("e4_parking_lot", "synchronous"),
             ("e4_parking_lot", "staggered"))
    for scenario, subcase in cases:
        source = os.path.join(V1, "cases", scenario, subcase)
        target = os.path.join(ROOT, "cases", scenario, subcase)
        os.makedirs(target, exist_ok=True)
        shutil.copy2(os.path.join(source, "config.txt"),
                     os.path.join(target, "config.txt"))
        for name in INPUTS:
            if os.path.isfile(os.path.join(source, name)):
                shutil.copy2(os.path.join(source, name),
                             os.path.join(target, name))
        rewrite(os.path.join(target, "config.txt"), {
            "CBAP_INCREASE_POLICY": 0,
            "CBAP_INCREASE_FRACTION": "0.10",
            "CBAP_INCREASE_ABSOLUTE_BPS": 2000000000,
            "CBAP_VERSION": "v1",
            "CBAP_INCREASE_AUDIT_FILE": "increase_policy_events.csv",
        })


def manifest_row(scenario, subcase, algorithm, seed, formal):
    mode, version, policy = IDENTITIES[algorithm]
    return {"run_id": "%s__%s__%s__seed%d" %
            (scenario, subcase, algorithm, seed),
            "scenario": scenario, "subcase": subcase,
            "algorithm_name": algorithm, "cbap_version": version,
            "increase_policy": policy, "increase_fraction": "0.10",
            "increase_absolute_bps": "2000000000", "cc_mode": mode,
            "seed": seed, "formal": int(formal)}


def write_manifest(name, rows):
    fields = ("run_id", "scenario", "subcase", "algorithm_name",
              "cbap_version", "increase_policy", "increase_fraction",
              "increase_absolute_bps", "cc_mode", "seed", "formal")
    os.makedirs(os.path.join(ROOT, "configs"), exist_ok=True)
    with open(os.path.join(ROOT, "configs", name), "w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def main_manifests():
    semantic = []
    semantic += [manifest_row("e1_single_old_single_new", "default", a, 1, 0)
                 for a in ("cbap_full_v1", "cbap_full_v11")]
    semantic += [manifest_row("e2_batch_incast", "default", a, 1, 0)
                 for a in ("independent_min_grant", "cbap_rateonly_v1",
                           "cbap_full_v1", "cbap_rateonly_v11",
                           "cbap_full_v11")]
    for subcase in ("synchronous", "staggered"):
        semantic += [manifest_row("e4_parking_lot", subcase, a, 1, 0)
                     for a in ("cbap_full_v1", "cbap_full_v11")]
    formal = []
    six = ("dcqcn", "hpcc_int", "cbap_rateonly_v1", "cbap_full_v1",
           "cbap_rateonly_v11", "cbap_full_v11")
    for scenario, subcase, algorithms in (
            ("e1_single_old_single_new", "default", six),
            ("e2_batch_incast", "default", six),
            ("e4_parking_lot", "staggered", six),
            ("e4_parking_lot", "synchronous",
             ("hpcc_int", "cbap_full_v1", "cbap_full_v11"))):
        for algorithm in algorithms:
            for seed in (1, 2, 3):
                formal.append(manifest_row(scenario, subcase, algorithm,
                                           seed, 1))
    write_manifest("semantic_manifest.csv", semantic)
    write_manifest("freeze_manifest.csv", formal)
    return len(semantic), len(formal)


def victim_case(count, access_gbps, message_mib):
    slug = "n%d_r%d_m%dm" % (count, access_gbps, message_mib)
    target = os.path.join(ROOT, "victim_cases", slug)
    os.makedirs(target, exist_ok=True)
    victim, hot, victim_dst = count, count + 1, count + 2
    sa, sb = count + 3, count + 4
    upstream_gbps = 2 * (count * access_gbps + 100)
    links = []
    for sender in range(count):
        links.append((sender, sa, "%dGbps" % access_gbps))
    links += [(victim, sa, "100Gbps"), (sa, sb, "%dGbps" % upstream_gbps),
              (sb, hot, "100Gbps"), (sb, victim_dst, "100Gbps")]
    with open(os.path.join(target, "topology.txt"), "w") as out:
        out.write("%d 2 %d\n%d %d\n" % (count + 5, len(links), sa, sb))
        for left, right, rate in links:
            out.write("%d %d %s 0.001ms 0\n" % (left, right, rate))
    size = message_mib * 1024 * 1024
    with open(os.path.join(target, "flow.txt"), "w") as out:
        out.write("%d\n" % (count + 1))
        out.write("%d %d 3 100 %d 0.000490000\n" %
                  (victim, victim_dst, 128 * 1024 * 1024))
        for sender in range(count):
            out.write("%d %d 3 100 %d 0.002990000\n" %
                      (sender, hot, size))
    with open(os.path.join(target, "fixed_paths.txt"), "w") as out:
        for flow in range(count + 1): out.write("%d -1\n" % flow)
    with open(os.path.join(target, "controlled_links.txt"), "w") as out:
        out.write("3\n1 %d %d %d 400000 0 1\n" %
                  (sa, count + 2, upstream_gbps * 1000000000))
        out.write("2 %d 2 100000000000 400000 0 1\n" % sb)
        out.write("3 %d 3 100000000000 400000 0 1\n" % sb)
    with open(os.path.join(target, "controlled_paths.txt"), "w") as out:
        out.write("%d\n0 2 1 3\n" % (count + 1))
        for flow in range(1, count + 1): out.write("%d 2 1 2\n" % flow)
    with open(os.path.join(target, "group_schedule.txt"), "w") as out:
        out.write("2\n0 -1 0 500000\n1 -1 0 3000000\n")
    with open(os.path.join(target, "rounds.txt"), "w") as out:
        out.write("%d\n" % (count + 1))
        out.write("0 0 0 1 %d 0 0 0 500000\n" % (128 * 1024 * 1024))
        for flow in range(1, count + 1):
            out.write("%d 0 1 %d %d 0 0 %d 3000000\n" %
                      (flow, count, size, flow - 1))
    open(os.path.join(target, "trace.txt"), "w").write("0\n")
    shutil.copy2(os.path.join(OLD, "cases", "e3_victim_flow", "pfc_on",
                              "config.txt"), os.path.join(target, "config.txt"))
    rate_values = sorted({50000000000, 100000000000,
                          upstream_gbps * 1000000000})
    map_count = len(rate_values)
    rates = " ".join(str(x) for pair in
                     ((value, 1600) for value in rate_values) for x in pair)
    mins = " ".join(str(x) for pair in
                    ((value, 400) for value in rate_values) for x in pair)
    pmax = " ".join(str(x) for pair in
                    ((value, 0.2) for value in rate_values) for x in pair)
    rewrite(os.path.join(target, "config.txt"), {
        "SIMULATOR_STOP_TIME": "0.15", "KMAX_MAP": "%d %s" % (map_count,rates),
        "KMIN_MAP": "%d %s" % (map_count,mins),
        "PMAX_MAP": "%d %s" % (map_count,pmax),
        "ROUND_TRACE_SELECTED_FLOWS": "0,1,2,3",
        "ROUND_TRACE_SELECTED_LINKS": "%d:%d,%d:2,%d:3" %
            (sa,count+2,sb,sb), "CBAP_INCREASE_POLICY": 0,
        "CBAP_INCREASE_FRACTION": "0.10",
        "CBAP_INCREASE_ABSOLUTE_BPS": 2000000000,
        "CBAP_VERSION": "v1", "CBAP_INCREASE_AUDIT_FILE": "/dev/null",
    })
    meta = {"scenario":"victim_calibration", "subcase":slug,
            "contributor_count":count, "contributor_access_rate_gbps":access_gbps,
            "contributor_message_mib":message_mib, "victim_flow_id":0,
            "contributor_flow_ids":list(range(1,count+1)),
            "shared_upstream_link_id":1, "true_root_link_id":2,
            "sa_sb_capacity_bps":upstream_gbps*1000000000,
            "sa_sb_is_capacity_bottleneck":False, "pfc_priority":3,
            "topology_roles":{"SA":sa,"SB":sb,"R_hot":hot,
                              "R_victim":victim_dst}}
    with open(os.path.join(target,"scenario_meta.json"),"w") as out:
        json.dump(meta,out,indent=2,sort_keys=True); out.write("\n")
    hashes={name:sha(os.path.join(target,name)) for name in
            ("topology.txt","flow.txt","rounds.txt","fixed_paths.txt",
             "controlled_links.txt","controlled_paths.txt","group_schedule.txt")}
    with open(os.path.join(target,"input_hashes.json"),"w") as out:
        json.dump(hashes,out,indent=2,sort_keys=True); out.write("\n")
    return slug


def victim_manifest():
    fields=("run_id","subcase","algorithm_name","cc_mode","pfc_enabled",
            "seed","contributor_count","access_rate_gbps","message_mib")
    rows=[]
    modes=(("open_loop_pfc_on",0,1),("dcqcn_pfc_on",1,1),
           ("dcqcn_pfc_off",1,0))
    for count in (4,8,16):
        for rate in (50,100):
            for message in (8,32,64):
                slug=victim_case(count,rate,message)
                for algorithm,mode,pfc in modes:
                    rows.append({"run_id":"%s__%s__seed1"%(slug,algorithm),
                                 "subcase":slug,"algorithm_name":algorithm,
                                 "cc_mode":mode,"pfc_enabled":pfc,"seed":1,
                                 "contributor_count":count,
                                 "access_rate_gbps":rate,"message_mib":message})
    with open(os.path.join(ROOT,"configs","victim_manifest.csv"),"w",newline="") as out:
        writer=csv.DictWriter(out,fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    return len(rows)


def main():
    copy_main_cases()
    semantic,formal=main_manifests()
    victim=victim_manifest()
    print("semantic=%d formal=%d victim=%d"%(semantic,formal,victim))


if __name__=="__main__": main()
