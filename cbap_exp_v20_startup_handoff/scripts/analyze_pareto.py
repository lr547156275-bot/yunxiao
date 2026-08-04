#!/usr/bin/env python3
import csv
import gzip
import hashlib
import json
import math
import os
import statistics

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(ROOT, ".."))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def percentile(values, p):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * p
    low = int(math.floor(position)); high = int(math.ceil(position))
    return ordered[low] if low == high else (ordered[low] * (high-position) +
                                             ordered[high] * (position-low))


def csv_rows(path):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", newline="") as stream:
        return list(csv.DictReader(stream))


def flow_metrics(run):
    rows = csv_rows(os.path.join(run, "flow_summary.csv"))
    fct = [float(r["fct"]) * 1e6 for r in rows]
    throughputs = []
    for row in rows:
        duration = float(row["fct"])
        size = float(row["size_bytes"])
        if duration > 0:
            throughputs.append(size * 8 / duration / 1e9)
    return dict(fct_min_us=min(fct), fct_mean_us=statistics.mean(fct),
                fct_p99_us=percentile(fct, .99),
                flow_throughput_min_gbps=min(throughputs),
                flow_throughput_mean_gbps=statistics.mean(throughputs),
                flow_throughput_p99_gbps=percentile(throughputs, .99))


def load_run(run, fraction=None, source="v20"):
    result = json.load(open(os.path.join(run, "result_full_work.json")))
    legacy = json.load(open(os.path.join(run, "result.json")))
    pfc_rows = csv_rows(os.path.join(run, "pfc_events.csv"))
    metrics = flow_metrics(run)
    metrics.update(dict(source=source, scenario=result["scenario"],
                        algorithm=result["algorithm"],
                        queue_target_fraction=fraction,
                        newcomer_cct_us=result.get("newcomer_cct_us"),
                        batch_throughput_gbps=(result.get(
                            "newcomer_delivered_bytes", 0) * 8 /
                            max(result.get("newcomer_cct_us", 0), 1) / 1e3),
                        peak_queue_bytes=result.get("queue_peak_bytes"),
                        queue_auc_byte_us=result.get("queue_auc_byte_us"),
                        active_utilization=result.get(
                            "utilization_active_window"),
                        ecn_time_us=result.get("time_above_ecn_threshold_us"),
                        pfc_events=len(pfc_rows),
                        ecn_marks=legacy.get("ecn_marks"),
                        incumbent_remaining_bytes=result.get(
                            "incumbent_remaining_bytes"),
                        all_work_makespan_us=result.get("all_work_makespan_us"),
                        total_goodput_gbps=result.get("total_goodput_gbps"),
                        completion_skew_us=result.get(
                            "newcomer_completion_skew_us"),
                        control_messages=result.get(
                            "logical_control_message_count"),
                        control_bytes=result.get("logical_control_bytes")))
    return metrics


def input_signature(run):
    names = ("topology.txt", "flow.txt", "rounds.txt", "fixed_paths.txt",
             "controlled_links.txt", "controlled_paths.txt",
             "group_schedule.txt")
    return {name: sha256(os.path.join(run, name)) for name in names}


def matching_reference(scenario, algorithm, signature):
    roots = [os.path.join(REPO, x) for x in
             ("cbap_final_paper_experiments", "cbap_exp_v13_ratefloor_fix",
              "cbap_exp_v14_stable_handoff")]
    candidates = []
    for root in roots:
        for directory, _, files in os.walk(root):
            if ("result_full_work.json" not in files or
                    "completed.flag" not in files):
                continue
            try:
                result = json.load(open(os.path.join(
                    directory, "result_full_work.json")))
                if (result.get("scenario") != scenario or
                        result.get("algorithm") != algorithm):
                    continue
                if input_signature(directory) == signature:
                    candidates.append(directory)
            except (OSError, ValueError, KeyError):
                continue
    return sorted(candidates)[0] if candidates else None


def plot(rows, xkey, ykey, filename, xlabel, ylabel):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    scenarios = sorted(set(r["scenario"] for r in rows if r["source"] == "v20"))
    for scenario in scenarios:
        selected = sorted((r for r in rows if r["scenario"] == scenario and
                           r["source"] == "v20"),
                          key=lambda r: float(r["queue_target_fraction"]))
        ax.plot([float(r[xkey]) for r in selected],
                [float(r[ykey]) for r in selected], marker="o", label=scenario)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=.25)
    ax.legend(fontsize=7)
    fig.tight_layout()
    for suffix in ("svg", "pdf"):
        fig.savefig(os.path.join(ROOT, "figures", "%s.%s" %
                                 (filename, suffix)))
    plt.close(fig)


def main():
    manifest = list(csv.DictReader(open(os.path.join(
        ROOT, "configs", "pareto_manifest.csv"))))
    rows, missing = [], []
    signatures = {}
    for item in manifest:
        run = os.path.join(ROOT, "runs_pareto", item["scenario"],
                           item["algorithm_name"], "seed_%s" % item["seed"])
        if not os.path.isfile(os.path.join(run, "completed.flag")):
            missing.append(item["run_id"])
            continue
        rows.append(load_run(run, float(item["queue_target_fraction"])))
        signatures[item["scenario"]] = input_signature(run)
    for scenario, signature in sorted(signatures.items()):
        for algorithm in ("dcqcn", "hpcc_int", "cbap_init_only",
                          "cbap_full_v13_ratefloor_fix"):
            reference = matching_reference(scenario, algorithm, signature)
            if reference:
                rows.append(load_run(reference, None, "reused_reference"))

    fields = sorted(set(key for row in rows for key in row))
    output = os.path.join(ROOT, "processed", "pareto_metrics.csv")
    with open(output, "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    if len([r for r in rows if r["source"] == "v20"]) == 30:
        plot(rows, "peak_queue_bytes", "fct_mean_us",
             "fct_vs_peak_queue", "Peak queue (bytes)", "Mean FCT (us)")
        plot(rows, "queue_auc_byte_us", "fct_mean_us",
             "fct_vs_queue_auc", "Queue AUC (byte-us)", "Mean FCT (us)")
        plot(rows, "peak_queue_bytes", "batch_throughput_gbps",
             "throughput_vs_peak_queue", "Peak queue (bytes)",
             "Batch throughput (Gb/s)")
        plot(rows, "peak_queue_bytes", "active_utilization",
             "utilization_vs_peak_queue", "Peak queue (bytes)",
             "Active-window utilization")
    report = os.path.join(ROOT, "reports", "pareto_results.md")
    with open(report, "w") as stream:
        stream.write("# CBAP-v2.0 Pareto diagnostic results\n\n")
        stream.write("- Valid v2.0 runs: %d/30\n" %
                     len([r for r in rows if r["source"] == "v20"]))
        stream.write("- Reused hash-matched reference runs: %d\n" %
                     len([r for r in rows if r["source"] != "v20"]))
        stream.write("- Missing v2.0 runs: %d\n" % len(missing))
        stream.write("\nNo queue-target value is selected by this analyzer.\n")
    if missing:
        raise SystemExit("missing Pareto runs: %d" % len(missing))
    print("PARETO_ANALYSIS_COMPLETE v20=30")


if __name__ == "__main__":
    main()
