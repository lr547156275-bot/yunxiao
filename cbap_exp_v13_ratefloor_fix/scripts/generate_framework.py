#!/usr/bin/env python3
"""Create deterministic v1.3 inputs and manifests; never runs ns-3."""
import csv, hashlib, json, os, shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(ROOT, ".."))
V12 = os.path.join(REPO, "cbap_exp_v12_scoped", "cases", "core")

CASES = [
    ("fan32_msg1m_load80", "fan32_msg1m_load80"),
    ("fan64_msg64k_load80", "fan64_msg64k_load80"),
    ("fan64_msg256k_load80", "fan64_msg256k_load80"),
    ("fan64_msg1m_load80", "fan64_msg1m_load80"),
    ("fan64_msg4m_load80", "fan64_msg4m_load80"),
    ("zero_grant_pause_resume", "fan4_msg4m_load80"),
]
ALGOS = {
    "dctcp": (8, "baseline", "ALWAYS", 0),
    "dcqcn": (1, "baseline", "ALWAYS", 0),
    "hpcc_int": (3, "baseline", "ALWAYS", 0),
    "cbap_full_v12_scoped": (24, "v1.2", "SHARED_BATCH_OVERSUBSCRIPTION", 0),
    "cbap_full_v13_ratefloor_fix": (25, "v1.3", "SHARED_BATCH_OVERSUBSCRIPTION", 1),
}


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def copy_cases():
    out = os.path.join(ROOT, "cases")
    os.makedirs(out, exist_ok=True)
    for name, source in CASES:
        src, dst = os.path.join(V12, source), os.path.join(out, name)
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        meta_path = os.path.join(dst, "scenario_meta.json")
        meta = json.load(open(meta_path))
        meta["scenario"] = name
        if name == "zero_grant_pause_resume":
            meta.update({
                "diagnostic_only": True,
                "ratefloor_zero_test_flow": 1,
                "ratefloor_zero_start_epoch": 610,
                "ratefloor_zero_end_epoch": 613,
                "minimum_zero_pause_epochs": 2,
            })
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2, sort_keys=True); f.write("\n")
        names = [x for x in os.listdir(dst) if os.path.isfile(os.path.join(dst, x))]
        with open(os.path.join(dst, "v13_input_hashes.json"), "w") as f:
            json.dump({x: digest(os.path.join(dst, x)) for x in names
                       if x != "v13_input_hashes.json"}, f,
                      indent=2, sort_keys=True); f.write("\n")


def manifest_row(scenario, algorithm, semantic_zero=False):
    mode, version, scope, floor = ALGOS[algorithm]
    return {
        "run_id": "%s__%s__seed1" % (scenario, algorithm),
        "scenario": scenario, "algorithm_name": algorithm,
        "cc_mode": mode, "cbap_version": version,
        "scope_policy": scope, "rate_floor_policy": floor,
        "seed": 1, "semantic_zero_test": int(semantic_zero),
        "semantic_zero_flow": 1 if semantic_zero else 0,
        "semantic_zero_start_epoch": 610 if semantic_zero else 0,
        "semantic_zero_end_epoch": 613 if semantic_zero else 0,
    }


def write_manifest(name, rows):
    os.makedirs(os.path.join(ROOT, "configs"), exist_ok=True)
    with open(os.path.join(ROOT, "configs", name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)


def main():
    copy_cases()
    semantic = [
        manifest_row("fan64_msg1m_load80", "cbap_full_v12_scoped"),
        manifest_row("fan64_msg1m_load80", "cbap_full_v13_ratefloor_fix"),
        manifest_row("fan64_msg4m_load80", "cbap_full_v13_ratefloor_fix"),
        manifest_row("fan32_msg1m_load80", "cbap_full_v13_ratefloor_fix"),
        manifest_row("zero_grant_pause_resume", "cbap_full_v13_ratefloor_fix", True),
    ]
    reduced = []
    for scenario in ["fan32_msg1m_load80", "fan64_msg64k_load80",
                     "fan64_msg256k_load80", "fan64_msg1m_load80",
                     "fan64_msg4m_load80"]:
        for algorithm in ["dctcp", "dcqcn", "hpcc_int",
                          "cbap_full_v12_scoped",
                          "cbap_full_v13_ratefloor_fix"]:
            reduced.append(manifest_row(scenario, algorithm))
    write_manifest("semantic_manifest.csv", semantic)
    write_manifest("reduced_manifest.csv", reduced)
    print("semantic_runs=5 reduced_runs=25")


if __name__ == "__main__":
    main()
