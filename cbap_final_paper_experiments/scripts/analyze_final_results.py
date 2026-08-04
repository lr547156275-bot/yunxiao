#!/usr/bin/env python3
"""Analyze only completed final-paper runs with full-work metrics."""
import csv
import json
import math
import os
import statistics

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROCESSED = os.path.join(ROOT, "processed")
REPORTS = os.path.join(ROOT, "reports")
ALGORITHMS = ("dctcp", "dcqcn", "timely", "hpcc_int", "bop_qb",
              "independent_min_grant", "cbap_full_v13_ratefloor_fix")
BASELINES = ("dcqcn", "timely", "hpcc_int", "dctcp", "bop_qb",
             "independent_min_grant")
METRICS = ("newcomer_cct_us", "newcomer_median_fct_us",
           "newcomer_max_fct_us", "newcomer_completion_skew_us",
           "incumbent_completion_time_us", "incumbent_remaining_fraction",
           "all_work_makespan_us", "total_goodput_gbps", "queue_peak_bytes",
           "queue_auc_byte_us", "queue_p95_time_weighted_bytes",
           "utilization_active_window", "time_above_ecn_threshold_us",
           "logical_control_message_count", "logical_control_bytes")
ROOTS = {"single_bottleneck": "runs_single_bottleneck",
         "release_skew": "runs_release_skew",
         "multibottleneck": "runs_multibottleneck", "clos": "runs_clos",
         "randomized": "runs_randomized", "ablation": "runs_ablation"}


def number(value):
    return float(value) if isinstance(value, (int, float)) and math.isfinite(value) else None


def write(path, rows, fields=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fields = fields or (list(rows[0]) if rows else ["status"])
    with open(path, "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def load():
    manifests = list(csv.DictReader(open(os.path.join(ROOT, "manifests", "all_runs.csv"))))
    rows, missing, invalid, suspicious = [], [], [], []
    for manifest in manifests:
        run = os.path.join(ROOT, ROOTS[manifest["experiment_family"]], manifest["run_id"])
        path = os.path.join(run, "result_full_work.json")
        if not os.path.isfile(path):
            missing.append({"run_id": manifest["run_id"], "reason": "missing_result_full_work"}); continue
        try:
            result = json.load(open(path))
        except Exception as error:
            invalid.append({"run_id": manifest["run_id"], "reason": "json:" + str(error)}); continue
        if not os.path.isfile(os.path.join(run, "completed.flag")):
            invalid.append({"run_id": manifest["run_id"], "reason": "missing_completed_flag"}); continue
        row = dict(manifest)
        for key, value in result.items():
            if not isinstance(value, (dict, list)): row[key] = value
        rows.append(row)
        for finding in result.get("suspicious_findings", []):
            suspicious.append({"run_id": manifest["run_id"], "finding": finding})
    return manifests, rows, missing, invalid, suspicious


def aggregates(rows):
    grouped = {}
    for row in rows:
        key = (row["experiment_family"], row["scenario_id"], row["algorithm"])
        grouped.setdefault(key, []).append(row)
    out = []
    for key, values in sorted(grouped.items()):
        item = {"experiment_family": key[0], "scenario_id": key[1],
                "algorithm": key[2], "sample_count": len(values)}
        for metric in METRICS:
            samples = [number(row.get(metric)) for row in values]
            samples = [value for value in samples if value is not None]
            item[metric + "_median"] = statistics.median(samples) if samples else ""
            item[metric + "_min"] = min(samples) if samples else ""
            item[metric + "_max"] = max(samples) if samples else ""
            if samples:
                ordered = sorted(samples); q1 = ordered[(len(ordered)-1)//4]
                q3 = ordered[(3*(len(ordered)-1))//4]
                item[metric + "_iqr"] = q3-q1
            else: item[metric + "_iqr"] = ""
        out.append(item)
    return out


def paired(rows, baseline):
    lookup = {(r["experiment_family"], r["scenario_id"], r["seed"], r["algorithm"]): r
              for r in rows}
    out = []
    for row in rows:
        if row["algorithm"] != "cbap_full_v13_ratefloor_fix": continue
        key = (row["experiment_family"], row["scenario_id"], row["seed"], baseline)
        if key not in lookup: continue
        base = lookup[key]
        item = {"experiment_family": row["experiment_family"],
                "scenario_id": row["scenario_id"], "seed": row["seed"],
                "baseline": baseline}
        for metric in METRICS:
            new, old = number(row.get(metric)), number(base.get(metric))
            item["cbap_" + metric] = new if new is not None else ""
            item["baseline_" + metric] = old if old is not None else ""
            item[metric + "_relative_percent"] = (
                (new-old)/old*100 if new is not None and old not in (None, 0) else "")
        out.append(item)
    return out


def subset(rows, family=None, fields=()):
    result = []
    for row in rows:
        if family and row["experiment_family"] != family: continue
        result.append({key: row.get(key, "") for key in
                       ("run_id", "experiment_family", "scenario_id", "algorithm",
                        "seed", "fanin", "message_bytes", "incumbent_load",
                        "release_skew_us", "workload", "oversubscription") + fields})
    return result


def main():
    os.makedirs(PROCESSED, exist_ok=True); os.makedirs(REPORTS, exist_ok=True)
    manifests, rows, missing, invalid, suspicious = load()
    write(os.path.join(PROCESSED, "summary_by_run.csv"), rows)
    write(os.path.join(PROCESSED, "summary_by_scenario.csv"), aggregates(rows))
    write(os.path.join(PROCESSED, "missing_runs.csv"), missing, ["run_id", "reason"])
    write(os.path.join(PROCESSED, "invalid_runs.csv"), invalid, ["run_id", "reason"])
    write(os.path.join(PROCESSED, "suspicious_runs.csv"), suspicious,
          ["run_id", "finding"])
    for baseline in BASELINES:
        label = {"independent_min_grant": "independent",
                 "hpcc_int": "hpcc"}.get(baseline, baseline)
        name = "paired_vs_%s.csv" % label
        write(os.path.join(PROCESSED, name), paired(rows, baseline))
    mappings = {
        "activation_map.csv": (None, ("scope_decision_count",)),
        "pareto_map.csv": (None, ("newcomer_cct_us", "queue_peak_bytes", "queue_auc_byte_us")),
        "fanin_scaling.csv": ("single_bottleneck", ("newcomer_cct_us", "queue_peak_bytes")),
        "message_scaling.csv": ("single_bottleneck", ("newcomer_cct_us", "queue_peak_bytes")),
        "load_scaling.csv": ("single_bottleneck", ("newcomer_cct_us", "incumbent_completion_time_us")),
        "skew_scaling.csv": ("release_skew", ("newcomer_cct_us", "queue_peak_bytes")),
        "multibottleneck_summary.csv": ("multibottleneck", ("newcomer_cct_us", "queue_peak_bytes", "total_goodput_gbps")),
        "clos_summary.csv": ("clos", ("newcomer_cct_us", "queue_peak_bytes")),
        "randomized_summary.csv": ("randomized", ("newcomer_cct_us", "queue_peak_bytes")),
        "ablation_summary.csv": ("ablation", ("newcomer_cct_us", "queue_peak_bytes")),
        "incumbent_summary.csv": (None, ("incumbent_completion_time_us", "incumbent_remaining_fraction")),
        "makespan_summary.csv": (None, ("all_work_makespan_us",)),
        "control_overhead.csv": (None, ("logical_control_message_count", "logical_control_bytes")),
    }
    for name, (family, fields) in mappings.items(): write(os.path.join(PROCESSED, name), subset(rows, family, fields))
    complete = len(rows) == len(manifests) and not missing and not invalid
    status = "FINAL_DATA_COMPLETE" if complete else "FINAL_DATA_INCOMPLETE"
    with open(os.path.join(REPORTS, "result_integrity_report.md"), "w") as stream:
        stream.write("# Result integrity\n\nStatus: **%s**\n\n" % status)
        stream.write("- Expected runs: %d\n- Valid runs: %d\n- Missing: %d\n- Invalid: %d\n" %
                     (len(manifests), len(rows), len(missing), len(invalid)))
        stream.write("\nNo missing or failed run is converted to zero.\n")
    print("%s valid=%d expected=%d missing=%d invalid=%d" %
          (status, len(rows), len(manifests), len(missing), len(invalid)))


if __name__ == "__main__": main()
