#!/usr/bin/env python3
"""Reclassify existing main-v1 results without altering or rerunning them."""
import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT.parent / "main_v1"
OUT = ROOT / "analysis"
FORMAL_CC = ("dctcp", "dcqcn", "timely", "hpcc_int")


def read(path):
    with open(path, newline="") as stream:
        return list(csv.DictReader(stream))


def write(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def pct(new, old):
    return (new - old) / old * 100.0 if old else "NA"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    summary = read(V1 / "analysis/scenario_summary.csv")
    lookup = {(r["scenario"], r["algorithm"], r["metric"]): float(r["mean"])
              for r in summary if r["mean"] not in ("", "NA")}
    scenarios = sorted({r["scenario"] for r in summary
                        if r["algorithm"] == "bop_qb" and
                        r["section"] == "main"})
    best_rows = []
    open_rows = []
    metrics = ("group_rct_mean_us", "queue_max_bytes",
               "queue_p95_bytes", "payload_goodput_gbps",
               "active_payload_utilization", "ecn_marks", "pfc_events")
    for scenario in scenarios:
        candidates = [(lookup[(scenario, algo, "group_rct_mean_us")], algo)
                      for algo in FORMAL_CC
                      if (scenario, algo, "group_rct_mean_us") in lookup]
        best_rct, best_algo = min(candidates)
        row = {"scenario": scenario,
               "best_formal_cc_baseline": best_algo,
               "best_formal_cc_rct_us": best_rct,
               "bop_qb_rct_us":
                   lookup[(scenario, "bop_qb", "group_rct_mean_us")]}
        row["bop_qb_rct_change_pct"] = pct(
            row["bop_qb_rct_us"], best_rct)
        for metric in ("queue_max_bytes", "payload_goodput_gbps",
                       "ecn_marks", "pfc_events"):
            base = lookup.get((scenario, best_algo, metric), math.nan)
            new = lookup.get((scenario, "bop_qb", metric), math.nan)
            row["best_" + metric] = base
            row["bop_qb_" + metric] = new
            row[metric + "_change_pct"] = pct(new, base)
        best_rows.append(row)
        o = {"scenario": scenario,
             "reference_name": "open_loop_no_endhost_cc",
             "runtime_pfc_status": "unverified",
             "semantic_caveat":
             "PFC configured but runtime pause behavior not verified"}
        for metric in metrics:
            o["open_loop_" + metric] = lookup.get(
                (scenario, "pfc_only", metric), math.nan)
            o["bop_qb_" + metric] = lookup.get(
                (scenario, "bop_qb", metric), math.nan)
        o["bop_qb_rct_cost_pct"] = pct(
            o["bop_qb_group_rct_mean_us"],
            o["open_loop_group_rct_mean_us"])
        o["bop_qb_queue_change_pct"] = pct(
            o["bop_qb_queue_max_bytes"], o["open_loop_queue_max_bytes"])
        open_rows.append(o)
    write(OUT / "best_cc_baseline_comparison.csv",
          list(best_rows[0]), best_rows)
    write(OUT / "open_loop_tradeoff.csv", list(open_rows[0]), open_rows)
    pairwise = [r for r in read(
        V1 / "analysis/pairwise_bop_vs_baselines.csv")
                if r["baseline_algorithm"] in FORMAL_CC]
    write(OUT / "pairwise_bop_vs_cc.csv", list(pairwise[0]), pairwise)
    reuse = read(ROOT / "config/reuse_manifest.csv")
    write(OUT / "reuse_summary.csv",
          ["expected_formal_runs", "reuse_allowed_runs",
           "reuse_rejected_runs", "main_v1_results_modified"],
          [{"expected_formal_runs": 273,
            "reuse_allowed_runs":
                sum(r["reuse_allowed"] == "true" for r in reuse),
            "reuse_rejected_runs":
                sum(r["reuse_allowed"] != "true" for r in reuse),
            "main_v1_results_modified": "false"}])
    current = lookup.get(("n32_64k_g50", "dcqcn",
                          "group_rct_mean_us"), math.nan)
    legacy = 213.184
    replay_path = ROOT / \
        "audit_runs/dcqcn_n32_current/dcqcn/seed_1/algorithm_summary.csv"
    replay_rct = "NOT_RUN"
    if replay_path.exists():
        replay_rows = read(replay_path)
        if replay_rows:
            replay_rct = replay_rows[0].get("group_rct_mean_us", "MISSING")
    n32 = [{
        "comparison": "legacy_report_vs_current_main_v1",
        "legacy_mean_rct_us": legacy, "current_mean_rct_us": current,
        "difference_us": current - legacy,
        "relative_change_pct": pct(current, legacy),
        "current_seed1_replay_rct_us": replay_rct,
        "legacy_config_unavailable": "true",
        "reproducibility_status": "DCQCN_DRIFT_UNRESOLVED",
        "reason": "legacy raw config/topology/flow/round inputs absent",
    }]
    write(OUT / "dcqcn_n32_reproducibility.csv", list(n32[0]), n32)
    write(OUT / "invalid_runs.csv",
          ["run_id", "reason"], [])
    (OUT / "suspicious_findings.md").write_text(
        "# Suspicious findings\n\n"
        "- Historical `pfc_only` data cannot establish runtime PFC dependence; "
        "the old trace lacks generation and actual sender-pause evidence.\n"
        "- Main-v1 queue metrics and PFC decisions refer to different objects "
        "(BEgressQueue versus SwitchMmu ingress accounting).\n"
        "- The archived n32 result reports 213.184 us, while current main-v1 "
        "is %.3f us; complete legacy inputs are unavailable, so the drift "
        "cannot be causally attributed.\n" % current)
    (OUT / "corrected_main_report.md").write_text(
        "# Corrected main-v2 baseline semantics\n\n"
        "The best formal CC baseline is selected only from DCTCP, DCQCN, "
        "TIMELY, and HPCC-INT. Historical `pfc_only` is renamed "
        "`open_loop_no_endhost_cc` and reported separately as an uncontrolled "
        "injection reference. PFC configured but runtime pause behavior not "
        "verified.\n\n"
        "Main-v2 contains 273 formal runs (225 main, 30 ablation, 18 wire "
        "fairness) and 45 separately classified open-loop historical runs. "
        "No simulation result was copied or changed. See the CSV files for "
        "the corrected per-scenario comparisons.\n\n"
        "The PFC semantic audit has not been run by this preparation task. "
        "Missing event evidence is recorded as pending, never as zero.\n")
    print("best_formal_scenarios=%d pairwise_rows=%d" %
          (len(best_rows), len(pairwise)))


if __name__ == "__main__":
    main()
