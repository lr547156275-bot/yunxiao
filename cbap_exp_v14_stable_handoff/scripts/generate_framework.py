#!/usr/bin/env python3
"""Generate the immutable v1.4 case copies and preregistered manifests.

This is input generation only.  It never invokes a simulator binary.
"""
import csv
import hashlib
import json
import os
import shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(ROOT, ".."))

SOURCES = {
    "fan32_msg1m_load80": "cbap_exp_v13_ratefloor_fix/cases/fan32_msg1m_load80",
    "fan64_msg64k_load80": "cbap_exp_v13_ratefloor_fix/cases/fan64_msg64k_load80",
    "fan64_msg256k_load80": "cbap_exp_v13_ratefloor_fix/cases/fan64_msg256k_load80",
    "fan64_msg1m_load80": "cbap_exp_v13_ratefloor_fix/cases/fan64_msg1m_load80",
    "fan64_msg4m_load80": "cbap_exp_v13_ratefloor_fix/cases/fan64_msg4m_load80",
    "fan64_msg1m_load95": "cbap_exp_v13_ratefloor_fix/cases/fan64_msg1m_load80",
}


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def copy_case(name, source):
    src = os.path.join(REPO, source)
    dst = os.path.join(ROOT, "cases", name)
    if not os.path.isdir(src):
        raise SystemExit("missing validated source case: %s" % src)
    os.makedirs(dst, exist_ok=True)
    for entry in os.listdir(src):
        a, b = os.path.join(src, entry), os.path.join(dst, entry)
        if os.path.isfile(a):
            shutil.copy2(a, b)

    # The validated load sweep changes only the incumbent access-link rate.
    # Apply the same existing transformation to the validated fan64 topology;
    # node IDs, flows, paths, ECN/PFC, and collective inputs remain identical.
    if name == "fan64_msg1m_load95":
        topology = os.path.join(dst, "topology.txt")
        text = open(topology).read()
        old = "0 66 80Gbps 0.001ms 0\n"
        if text.count(old) != 1:
            raise SystemExit("fan64 load80 topology no longer has expected incumbent link")
        with open(topology, "w") as f:
            f.write(text.replace(old, "0 66 95Gbps 0.001ms 0\n"))
    meta_path = os.path.join(dst, "scenario_meta.json")
    meta = json.load(open(meta_path)) if os.path.isfile(meta_path) else {}
    meta.update(v14_case=name, source_case=source, generated_only=True)
    if name == "fan64_msg1m_load95":
        meta.update(scenario=name, incumbent_offered_load_percent=95,
                    topology_transform="incumbent_access_80Gbps_to_95Gbps")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2, sort_keys=True); f.write("\n")
    names = sorted(x for x in os.listdir(dst)
                   if os.path.isfile(os.path.join(dst, x)))
    hashes = {x: digest(os.path.join(dst, x)) for x in names
              if x != "v14_input_hashes.json"}
    with open(os.path.join(dst, "v14_input_hashes.json"), "w") as f:
        json.dump(hashes, f, indent=2, sort_keys=True); f.write("\n")


def row(scenario, algorithm, mode, version, run_class, expected,
        force_root=0, recovery_until=0):
    return {
        "run_id": "%s__%s__seed1" % (scenario, algorithm),
        "scenario": scenario,
        "algorithm_name": algorithm,
        "cc_mode": mode,
        "cbap_version": version,
        "scope_policy": "SHARED_BATCH_OVERSUBSCRIPTION" if mode in (25, 26)
                        else "ALWAYS",
        "rate_floor_policy": 1 if mode in (25, 26) else 0,
        "seed": 1,
        "run_class": run_class,
        "expected_handoff": expected,
        "diagnostic_force_root": force_root,
        "diagnostic_recovery_until_epoch": recovery_until,
    }


def write_manifest(path, rows):
    fields = list(rows[0])
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)


def main():
    for name, source in SOURCES.items():
        copy_case(name, source)
    copy_case("diagnostic_persistent_root", SOURCES["fan64_msg1m_load80"])
    copy_case("diagnostic_recovery", SOURCES["fan64_msg1m_load80"])

    semantic = [
        row("fan64_msg1m_load80", "cbap_full_v14_stable_handoff", 26,
            "v1.4", "semantic", "required"),
        row("fan64_msg4m_load80", "cbap_full_v14_stable_handoff", 26,
            "v1.4", "semantic", "required_remaining"),
        row("fan64_msg1m_load95", "cbap_full_v14_stable_handoff", 26,
            "v1.4", "semantic", "conditional"),
        row("diagnostic_persistent_root", "cbap_full_v14_stable_handoff", 26,
            "v1.4", "semantic", "forbidden", force_root=1),
        row("diagnostic_recovery", "cbap_full_v14_stable_handoff", 26,
            "v1.4", "semantic", "after_recovery", recovery_until=6),
        row("fan64_msg64k_load80", "cbap_full_v14_stable_handoff", 26,
            "v1.4", "semantic", "optional"),
        row("fan64_msg4m_load80", "cbap_full_v13_ratefloor_fix", 25,
            "v1.3", "semantic", "shadow_only"),
    ]
    write_manifest(os.path.join(ROOT, "configs", "semantic_manifest.csv"),
                   semantic)

    cases = ["fan32_msg1m_load80", "fan64_msg64k_load80",
             "fan64_msg256k_load80", "fan64_msg1m_load80",
             "fan64_msg4m_load80", "fan64_msg1m_load95"]
    algorithms = [
        ("dcqcn", 1, "baseline"),
        ("hpcc_int", 3, "baseline"),
        ("cbap_init_only", 21, "v1"),
        ("cbap_full_v13_ratefloor_fix", 25, "v1.3"),
        ("cbap_full_v14_stable_handoff", 26, "v1.4"),
    ]
    validation = [row(case, name, mode, version, "validation", "measure")
                  for case in cases for name, mode, version in algorithms]
    write_manifest(os.path.join(ROOT, "configs", "validation_manifest.csv"),
                   validation)
    print("GENERATED semantic=%d validation=%d" %
          (len(semantic), len(validation)))


if __name__ == "__main__":
    main()
