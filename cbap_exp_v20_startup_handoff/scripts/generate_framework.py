#!/usr/bin/env python3
"""Materialize immutable CBAP-v2.0 inputs and preregistered manifests.

This script only copies existing validated inputs and writes manifests.  It
never invokes waf or an ns-3 binary.
"""
import csv
import hashlib
import json
import os
import shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(ROOT, ".."))

SOURCES = {
    "no_shared_link": "cbap_exp_v12_scoped/cases/scope/no_shared_link",
    "single_pending": "cbap_exp_v12_scoped/cases/scope/single_pending",
    "two_pending_low_demand":
        "cbap_exp_v12_scoped/cases/scope/two_pending_low_demand",
    "batch_incast": "cbap_exp_v12_scoped/cases/scope/batch_incast",
    "parking_lot_synchronous":
        "cbap_exp_v12_scoped/cases/scope/synchronous_parking_lot",
    "fan16_msg256k_load80":
        "cbap_final_paper_experiments/configs/cases/single_bottleneck/"
        "fan16_msg256k_load80",
    "fan64_msg256k_load80":
        "cbap_final_paper_experiments/configs/cases/single_bottleneck/"
        "fan64_msg256k_load80",
    "fan64_msg1m_load80":
        "cbap_final_paper_experiments/configs/cases/single_bottleneck/"
        "fan64_msg1m_load80",
    "fan64_msg4m_load80":
        "cbap_final_paper_experiments/configs/cases/single_bottleneck/"
        "fan64_msg4m_load80",
    "fan64_msg1m_load95":
        "cbap_final_paper_experiments/configs/cases/single_bottleneck/"
        "fan64_msg1m_load95",
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def copy_case(name, source):
    src = os.path.join(REPO, source)
    dst = os.path.join(ROOT, "cases", name)
    if not os.path.isdir(src):
        raise SystemExit("missing validated source case: %s" % src)
    os.makedirs(dst, exist_ok=True)
    for old in os.listdir(dst):
        path = os.path.join(dst, old)
        if os.path.isfile(path) or os.path.islink(path):
            os.unlink(path)
    for entry in sorted(os.listdir(src)):
        a, b = os.path.join(src, entry), os.path.join(dst, entry)
        if os.path.isfile(a):
            shutil.copy2(a, b)
    required = ("topology.txt", "flow.txt", "trace.txt", "config.txt",
                "rounds.txt", "fixed_paths.txt", "controlled_links.txt",
                "controlled_paths.txt", "group_schedule.txt")
    missing = [x for x in required if not os.path.isfile(os.path.join(dst, x))]
    if missing:
        raise SystemExit("case %s missing %s" % (name, ",".join(missing)))
    meta_path = os.path.join(dst, "scenario_meta.json")
    meta = json.load(open(meta_path)) if os.path.isfile(meta_path) else {}
    meta.update(scenario=name, v20_source_case=source,
                generated_only=True, algorithm_agnostic=True)
    with open(meta_path, "w") as stream:
        json.dump(meta, stream, indent=2, sort_keys=True)
        stream.write("\n")
    hashes = {}
    for entry in sorted(os.listdir(dst)):
        path = os.path.join(dst, entry)
        if os.path.isfile(path) and entry != "v20_input_hashes.json":
            hashes[entry] = sha256(path)
    with open(os.path.join(dst, "v20_input_hashes.json"), "w") as stream:
        json.dump(hashes, stream, indent=2, sort_keys=True)
        stream.write("\n")


def manifest_row(run_id, scenario, algorithm, mode, fraction, run_class,
                 semantic_id="", expected="MEASURE"):
    base = "DCQCN" if mode == 28 else "HPCC_INT"
    return dict(run_id=run_id, scenario=scenario,
                algorithm_name=algorithm, cc_mode=mode,
                cbap_version="v2.0", base_cc=base,
                queue_target_fraction=fraction, seed=1,
                run_class=run_class, semantic_id=semantic_id,
                expected=expected)


def write_manifest(name, rows):
    path = os.path.join(ROOT, "configs", name)
    with open(path, "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    for name, source in sorted(SOURCES.items()):
        copy_case(name, source)

    semantic_specs = [
        ("S1", "no_shared_link", 28, 0.25, "C0_NO_RISK"),
        ("S2", "single_pending", 28, 0.25, "C0_NO_RISK"),
        ("S3", "two_pending_low_demand", 29, 0.25, "C0_NO_RISK"),
        ("S4", "batch_incast", 28, 0.25, "C1_SINGLE_HOTSPOT"),
        ("S5", "parking_lot_synchronous", 28, 0.25, "C2_COMPLEX"),
        ("S6", "fan16_msg256k_load80", 28, 0.75,
         "CONTROLLED_QUEUE_BUILD"),
        ("S7", "fan64_msg1m_load95", 28, 0.0,
         "QUEUE_DRAIN"),
        ("S8", "fan64_msg1m_load80", 29, 0.25,
         "FRESH_FEEDBACK_HANDOFF"),
    ]
    semantic = []
    for sid, scenario, mode, fraction, expected in semantic_specs:
        algo = "cbap_v20_startup_handoff_%s" % (
            "dcqcn" if mode == 28 else "hpcc")
        run_id = "%s__%s__seed1" % (sid.lower(), algo)
        semantic.append(manifest_row(run_id, scenario, algo, mode, fraction,
                                     "semantic", sid, expected))
    write_manifest("semantic_manifest.csv", semantic)

    scenarios = ["fan16_msg256k_load80", "fan64_msg256k_load80",
                 "fan64_msg1m_load80", "fan64_msg4m_load80",
                 "fan64_msg1m_load95", "parking_lot_synchronous"]
    fractions = [0, 0.125, 0.25, 0.5, 0.75]
    pareto = []
    for scenario in scenarios:
        for fraction in fractions:
            tag = str(fraction).replace(".", "p")
            algo = "cbap_v20_startup_handoff_dcqcn_q%s" % tag
            run_id = "%s__%s__seed1" % (scenario, algo)
            pareto.append(manifest_row(run_id, scenario, algo, 28, fraction,
                                       "pareto"))
    write_manifest("pareto_manifest.csv", pareto)

    references = []
    for scenario in scenarios:
        for algo in ("dcqcn", "hpcc_int", "cbap_init_only",
                     "cbap_full_v13_ratefloor_fix"):
            references.append(dict(scenario=scenario, algorithm_name=algo,
                policy="reuse_only_if_input_hashes_match",
                search_roots="cbap_final_paper_experiments;"
                             "cbap_exp_v13_ratefloor_fix;"
                             "cbap_exp_v14_stable_handoff"))
    write_manifest("reference_sources.csv", references)
    print("GENERATED semantic=%d pareto=%d references=%d" %
          (len(semantic), len(pareto), len(references)))


if __name__ == "__main__":
    main()
