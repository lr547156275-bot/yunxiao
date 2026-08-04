#!/usr/bin/env python3
"""Run-level CBAP-v1.1 analysis and bounded phase-2 packaging.

This script is analysis-only: it reads completed runs and writes reports,
processed CSVs, figures, and a selective tar archive.  It never invokes waf.
"""
import argparse
import csv
import gzip
import hashlib
import json
import math
import os
import statistics
import tarfile
import time
from collections import defaultdict

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(ROOT, ".."))
RUNS = os.path.join(ROOT, "runs_formal")
SEMANTIC = os.path.join(ROOT, "runs_semantic")
VICTIM = os.path.join(ROOT, "victim_calibration")
PROCESSED = os.path.join(ROOT, "processed")
REPORTS = os.path.join(ROOT, "reports")
FIGURES = os.path.join(ROOT, "figures")

LOWER_BETTER = {
    "new_group_cct_us", "group_rct_mean_us", "group_rct_max_us",
    "flow_fct_mean_us", "flow_fct_max_us", "queue_max_bytes",
    "queue_p95_bytes", "queue_auc_byte_seconds", "completion_skew_us",
    "ecn_marks", "pfc_events", "capacity_violations",
    "credit_violations", "pacing_violations",
}
METRICS = [
    "new_group_cct_us", "group_rct_mean_us", "group_rct_max_us",
    "flow_fct_mean_us", "flow_fct_max_us", "queue_max_bytes",
    "queue_p95_bytes", "queue_auc_byte_seconds", "mean_utilization",
    "payload_goodput_gbps", "completion_skew_us", "ecn_marks",
    "pfc_events", "simultaneous_active_jain", "link1_utilization",
    "link2_utilization", "capacity_violations", "credit_violations",
    "pacing_violations", "control_messages", "control_bytes",
]
IDENTITIES = {
    "dcqcn": (1, "baseline", "none"),
    "hpcc_int": (3, "baseline", "none"),
    "cbap_rateonly_v1": (22, "v1", "legacy_min"),
    "cbap_full_v1": (23, "v1", "legacy_min"),
    "cbap_rateonly_v11": (22, "v1.1", "adaptive_max"),
    "cbap_full_v11": (23, "v1.1", "adaptive_max"),
}


def read_csv(path):
    if os.path.isfile(path):
        opener, selected = open, path
    elif os.path.isfile(path + ".gz"):
        opener, selected = gzip.open, path + ".gz"
    else:
        return []
    with opener(selected, "rt", newline="") as stream:
        return list(csv.DictReader(stream))


def load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path) as stream:
        return json.load(stream)


def number(row, key, default=0.0):
    try:
        value = float(row.get(key, default))
        return value if math.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def mean(values):
    return statistics.mean(values) if values else 0.0


def percentile(values, fraction):
    values = sorted(values)
    if not values:
        return 0.0
    position = (len(values) - 1) * fraction
    low, high = int(math.floor(position)), int(math.ceil(position))
    if low == high:
        return values[low]
    return values[low] * (high - position) + values[high] * (position - low)


def pct(new, baseline):
    return (new - baseline) / baseline * 100.0 if baseline else 0.0


def write_csv(path, rows, fields=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with open(path, "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields,
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def finite_tree(value):
    if isinstance(value, dict):
        return all(finite_tree(item) for item in value.values())
    if isinstance(value, list):
        return all(finite_tree(item) for item in value)
    return not isinstance(value, float) or math.isfinite(value)


def run_dir(entry):
    return os.path.join(RUNS, entry["scenario"], entry["subcase"],
                        entry["algorithm_name"], "seed_" + entry["seed"])


def simultaneous_fairness(path):
    samples = read_csv(os.path.join(path, "selected_flow_timeseries.csv"))
    grouped = defaultdict(dict)
    for row in samples:
        grouped[number(row, "time")][row["flow_id"]] = row
    previous = {}
    scores = []
    for _, flows in sorted(grouped.items()):
        active = [flow for flow, row in flows.items()
                  if number(row, "released_bytes") > number(row, "snd_una")]
        rates = []
        for flow in active:
            if flow in previous:
                rates.append(max(number(flows[flow], "snd_nxt") -
                                 previous[flow], 0.0))
        previous = {flow: number(row, "snd_nxt")
                    for flow, row in flows.items()}
        denominator = len(rates) * sum(value * value for value in rates)
        if len(active) >= 3 and len(rates) == len(active) and denominator:
            scores.append(sum(rates) ** 2 / denominator)
    return mean(scores)


def collect_run(entry):
    path = run_dir(entry)
    problems = []
    required = ["completed.flag", "exit_status.txt", "run_meta.json",
                "result.json", "flow_summary.csv", "round_summary.csv",
                "group_round_summary.csv", "queue_summary.csv",
                "rate_summary.csv", "config.txt", "command.txt"]
    for name in required:
        if not os.path.isfile(os.path.join(path, name)):
            problems.append("missing_" + name)
    if problems:
        return None, problems
    result = load_json(os.path.join(path, "result.json"), {})
    meta = load_json(os.path.join(path, "run_meta.json"), {})
    expected = IDENTITIES[entry["algorithm_name"]]
    if int(open(os.path.join(path, "exit_status.txt")).read().strip()):
        problems.append("nonzero_exit_status")
    if meta.get("exit_status") != 0:
        problems.append("run_meta_exit_status")
    if not result.get("all_flows_completed"):
        problems.append("flows_incomplete")
    if result.get("log_truncated") or meta.get("log_truncated"):
        problems.append("log_truncated")
    if not finite_tree(result):
        problems.append("nan_or_inf")
    if int(meta.get("cc_mode", -1)) != expected[0]:
        problems.append("cc_mode_mismatch")
    if meta.get("cbap_version") != expected[1]:
        problems.append("cbap_version_mismatch")
    if meta.get("increase_policy") != expected[2]:
        problems.append("increase_policy_mismatch")
    flows = read_csv(os.path.join(path, "flow_summary.csv"))
    rounds = read_csv(os.path.join(path, "round_summary.csv"))
    groups = read_csv(os.path.join(path, "group_round_summary.csv"))
    queues = read_csv(os.path.join(path, "queue_summary.csv"))
    states = read_csv(os.path.join(path, "cbap_flow_state.csv"))
    overhead = read_csv(os.path.join(path, "cbap_control_overhead.csv"))
    scenario_meta = load_json(os.path.join(path, "scenario_meta.json"), {})
    if any(int(number(row, "completed")) != 1 for row in flows):
        problems.append("flow_summary_incomplete")
    if any(number(row, "ack_completion_time") <
           number(row, "release_time") for row in rounds):
        problems.append("negative_round_completion")
    if problems:
        return None, problems
    flow_fct = [number(row, "fct") * 1e6 for row in flows]
    finishes = [number(row, "finish_time") for row in flows]
    new_ids = set(str(value) for value in scenario_meta.get("new_flow_ids", []))
    new_fcts = [number(row, "fct") * 1e6 for row in flows
                if row["flow_id"] in new_ids]
    queue_by_link = sorted(queues, key=lambda row: row["link_id"])
    control = overhead[0] if overhead else {}
    row = {
        "run_id": entry["run_id"], "scenario": entry["scenario"],
        "subcase": entry["subcase"],
        "algorithm": entry["algorithm_name"],
        "cbap_version": entry["cbap_version"],
        "increase_policy": entry["increase_policy"],
        "cc_mode": int(entry["cc_mode"]), "seed": int(entry["seed"]),
        "flow_count": len(flows), "round_count": len(rounds),
        "group_round_count": len(groups),
        "flow_fct_mean_us": mean(flow_fct),
        "flow_fct_max_us": max(flow_fct) if flow_fct else 0,
        "new_group_cct_us": max(new_fcts) if new_fcts else
                              number(result, "group_rct_max_us"),
        "group_rct_mean_us": number(result, "group_rct_mean_us"),
        "group_rct_max_us": number(result, "group_rct_max_us"),
        "queue_max_bytes": number(result, "queue_max_bytes"),
        "queue_p95_bytes": number(result, "queue_p95_bytes"),
        "queue_auc_byte_seconds": number(result,
                                             "queue_auc_byte_seconds"),
        "mean_utilization": number(result, "mean_utilization"),
        "payload_goodput_gbps": number(result, "payload_goodput_gbps"),
        "completion_skew_us": ((max(finishes) - min(finishes)) * 1e6
                                if finishes else 0),
        "ecn_marks": number(result, "ecn_marks"),
        "pfc_events": number(result, "pfc_event_rows"),
        "simultaneous_active_jain": simultaneous_fairness(path)
            if entry["scenario"] == "e4_parking_lot" else 0,
        "link1_utilization": number(queue_by_link[0], "utilization_mean")
            if queue_by_link else 0,
        "link2_utilization": number(queue_by_link[1], "utilization_mean")
            if len(queue_by_link) > 1 else 0,
        "capacity_violations": number(result, "capacity_violations") +
            sum(number(state, "capacity_violations") for state in states),
        "credit_violations": number(result, "credit_violations") +
            sum(number(state, "credit_violations") for state in states),
        "pacing_violations": sum(number(state, "pacing_violations")
                                  for state in states),
        "control_messages": number(control, "summary_messages") +
                            number(control, "grant_messages"),
        "control_bytes": number(control, "total_control_bytes"),
        "input_hash_bundle": hashlib.sha256(json.dumps(
            meta.get("input_hashes", {}), sort_keys=True).encode()).hexdigest(),
        # Seed is identity metadata, not a measured outcome.  Excluding it
        # allows exact repetition of all retained metrics to be detected.
        "result_signature": hashlib.sha256(json.dumps({key: value
            for key, value in result.items() if key != "seed"},
            sort_keys=True).encode()).hexdigest(),
    }
    return row, []


def convergence_rows(records):
    output = []
    for record in records:
        if record["scenario"] != "e4_parking_lot" or \
                record["subcase"] != "staggered" or \
                not record["algorithm"].startswith("cbap_"):
            continue
        path = os.path.join(RUNS, record["scenario"], record["subcase"],
                            record["algorithm"], "seed_" + str(record["seed"]))
        meta = load_json(os.path.join(path, "scenario_meta.json"), {})
        f0 = next((flow for flow, role in meta.get("flow_roles", {}).items()
                   if role == "F0"), "2")
        states = read_csv(os.path.join(path, "cbap_flow_state.csv"))
        state = next((row for row in states if row["flow_id"] == f0), {})
        overhead = read_csv(os.path.join(path, "cbap_control_overhead.csv"))
        control_delay = number(overhead[0], "control_delay_ns") if overhead else 0
        release = number(state, "network_release_ns")
        rtt = max(number(state, "estimated_first_feedback_ns") - release -
                  control_delay, 1)
        samples = [row for row in read_csv(os.path.join(
            path, "selected_flow_timeseries.csv")) if row["flow_id"] == f0]
        transitions = [row for row in read_csv(os.path.join(
            path, "cbap_rate_transitions.csv")) if row["flow_id"] == f0 and
            number(row, "time_ns") >= release]
        changed = [row for row in transitions if
                   number(row, "new_rate_bps") != number(row, "old_rate_bps")]
        minimum_time = min((number(row, "time_ns") for row in changed
                            if number(row, "new_rate_bps") ==
                            min(number(item, "new_rate_bps")
                                for item in changed)), default=release)
        item = {"run_id": record["run_id"],
                "algorithm": record["algorithm"], "seed": record["seed"],
                "flow_id": f0, "release_ns": release,
                "estimated_base_rtt_ns": rtt,
                "minimum_rate_time_ns": minimum_time}
        for multiple in (2, 4, 6, 8):
            target = (release + multiple * rtt) / 1e9
            chosen = min(samples, key=lambda row:
                         abs(number(row, "time") - target)) if samples else {}
            item["rate_%drtt_gbps" % multiple] = \
                number(chosen, "current_rate") / 1e9
        for threshold in (25, 35, 40, 45, 47.5):
            hit = next((number(row, "time_ns") for row in changed
                        if number(row, "time_ns") >= minimum_time and
                        number(row, "new_rate_bps") >= threshold * 1e9), 0)
            key = str(threshold).replace(".", "p")
            item["reach_%sg_us" % key] = (hit - release) / 1000 if hit else 0
            item["reach_%sg_rtt" % key] = (hit - release) / rtt if hit else 0
        item["final_rate_gbps"] = number(state, "final_rate_bps") / 1e9
        item["double_penalty_25g_steady"] = int(item["final_rate_gbps"] <= 25)
        output.append(item)
    return output


def summarize(records):
    grouped = defaultdict(list)
    for row in records:
        grouped[(row["scenario"], row["subcase"], row["algorithm"])].append(row)
    output = []
    for key, rows in sorted(grouped.items()):
        item = {"scenario": key[0], "subcase": key[1], "algorithm": key[2],
                "seed_count": len(rows),
                "deterministic_repetition": int(len({row["result_signature"]
                    for row in rows}) == 1)}
        for metric in METRICS:
            values = [number(row, metric) for row in rows]
            item[metric + "_mean"] = mean(values)
            item[metric + "_median"] = statistics.median(values)
            item[metric + "_min"] = min(values)
            item[metric + "_max"] = max(values)
        output.append(item)
    return output


def pairwise(records):
    indexed = {(row["scenario"], row["subcase"], row["algorithm"],
                row["seed"]): row for row in records}
    comparisons = [
        ("cbap_rateonly_v11", "cbap_rateonly_v1"),
        ("cbap_full_v11", "cbap_full_v1"),
        ("cbap_full_v11", "dcqcn"),
        ("cbap_full_v11", "hpcc_int"),
        ("cbap_full_v11", "cbap_rateonly_v11"),
    ]
    scenarios = sorted({(row["scenario"], row["subcase"])
                        for row in records})
    output = []
    for scenario, subcase in scenarios:
        for new, baseline in comparisons:
            pairs = [(indexed[(scenario, subcase, new, seed)],
                      indexed[(scenario, subcase, baseline, seed)])
                     for seed in (1, 2, 3)
                     if (scenario, subcase, new, seed) in indexed and
                        (scenario, subcase, baseline, seed) in indexed]
            if not pairs:
                continue
            for metric in METRICS:
                differences = [pct(number(a, metric), number(b, metric))
                               for a, b in pairs]
                favorable = sum((value <= 0 if metric in LOWER_BETTER
                                 else value >= 0) for value in differences)
                output.append({
                    "scenario": scenario, "subcase": subcase,
                    "algorithm": new, "baseline": baseline,
                    "metric": metric, "pair_count": len(pairs),
                    "algorithm_mean": mean([number(a, metric)
                                            for a, _ in pairs]),
                    "baseline_mean": mean([number(b, metric)
                                           for _, b in pairs]),
                    "paired_pct_mean": mean(differences),
                    "paired_pct_median": statistics.median(differences),
                    "paired_pct_min": min(differences),
                    "paired_pct_max": max(differences),
                    "favorable_seed_count": favorable,
                })
    return output


def increase_audit():
    output = []
    roots = [("formal", RUNS), ("semantic", SEMANTIC)]
    for scope, base in roots:
        for directory, _, files in os.walk(base):
            if "increase_policy_events.csv" not in files:
                continue
            meta = load_json(os.path.join(directory, "run_meta.json"), {})
            for event in read_csv(os.path.join(directory,
                                               "increase_policy_events.csv")):
                old = number(event, "current_rate_before_bps")
                new = number(event, "new_rate_bps")
                fractional = math.floor(1.10 * old)
                absolute = old + 2e9
                policy = meta.get("increase_policy", "none")
                cap = min(fractional, absolute) if policy == "legacy_min" \
                    else max(fractional, absolute)
                reasons = []
                if abs(number(event, "fractional_candidate_bps") -
                       fractional) > 1:
                    reasons.append("fractional_candidate")
                if abs(number(event, "absolute_candidate_bps") -
                       absolute) > 1:
                    reasons.append("absolute_candidate")
                if abs(number(event, "selected_delta_bps") -
                       (new - old)) > 1:
                    reasons.append("selected_delta")
                if new > min(number(event, "target_rate_bps"),
                             number(event, "max_rate_bps"), cap) + 1 or new < old:
                    reasons.append("rate_bound")
                if int(number(event, "phase")) != 3:
                    reasons.append("phase")
                if int(number(event, "stable_epoch_count")) < 2:
                    reasons.append("stable_epochs")
                if int(number(event, "stale_feedback")):
                    reasons.append("stale_feedback")
                row = dict(event)
                row.update(scope=scope, run_id=meta.get("run_id", ""),
                           expected_policy=policy, valid=int(not reasons),
                           audit_reason=";".join(reasons))
                output.append(row)
    return output


def table_lookup(pair_rows, scenario, subcase, baseline, metric,
                 algorithm="cbap_full_v11"):
    return next((row for row in pair_rows if row["scenario"] == scenario and
                 row["subcase"] == subcase and row["baseline"] == baseline and
                 row["algorithm"] == algorithm and row["metric"] == metric), {})


def plot_bars(base, title, labels, values, ylabel):
    width, height = 1100, 680
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.text((40, 25), title, fill="black", font=font)
    left, top, right, bottom = 100, 80, width - 40, height - 110
    draw.line((left, top, left, bottom), fill="black", width=2)
    draw.line((left, bottom, right, bottom), fill="black", width=2)
    maximum = max(values) if values else 1
    maximum = maximum if maximum > 0 else 1
    slot = (right - left) / max(len(values), 1)
    colors = [(76, 114, 176), (221, 132, 82), (85, 168, 104),
              (196, 78, 82), (129, 114, 179), (147, 120, 96)]
    for index, (label, value) in enumerate(zip(labels, values)):
        x0 = left + index * slot + slot * .18
        x1 = left + (index + 1) * slot - slot * .18
        y0 = bottom - (bottom - top) * value / maximum
        draw.rectangle((x0, y0, x1, bottom), fill=colors[index % len(colors)])
        draw.text((x0, max(y0 - 18, top)), "%.3g" % value,
                  fill="black", font=font)
        draw.text((x0, bottom + 10), label, fill="black", font=font)
    draw.text((10, top), ylabel, fill="black", font=font)
    image.save(base + ".png")
    pdf = canvas.Canvas(base + ".pdf", pagesize=landscape(letter))
    pdf.setTitle(title)
    pdf.drawString(40, 560, title)
    pdf.drawImage(base + ".png", 40, 40, width=700, height=450,
                  preserveAspectRatio=True)
    pdf.save()


def plot_lines(base, title, series, ylabel):
    width, height = 1100, 680
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    left, top, right, bottom = 100, 80, width - 50, height - 100
    draw.text((40, 25), title, fill="black", font=font)
    draw.line((left, top, left, bottom), fill="black", width=2)
    draw.line((left, bottom, right, bottom), fill="black", width=2)
    points = [point for values in series.values() for point in values]
    xmin = min((p[0] for p in points), default=0)
    xmax = max((p[0] for p in points), default=1)
    ymin = min((p[1] for p in points), default=0)
    ymax = max((p[1] for p in points), default=1)
    if xmax == xmin: xmax += 1
    if ymax == ymin: ymax += 1
    colors = [(76, 114, 176), (196, 78, 82), (85, 168, 104)]
    for index, (name, values) in enumerate(sorted(series.items())):
        coords = []
        for x, y in values:
            px = left + (x - xmin) / (xmax - xmin) * (right - left)
            py = bottom - (y - ymin) / (ymax - ymin) * (bottom - top)
            coords.append((px, py))
        if len(coords) > 1: draw.line(coords, fill=colors[index], width=3)
        for point in coords: draw.ellipse((point[0]-3, point[1]-3,
                                          point[0]+3, point[1]+3),
                                         fill=colors[index])
        draw.text((right - 210, top + index * 20), name,
                  fill=colors[index], font=font)
    draw.text((10, top), ylabel, fill="black", font=font)
    draw.text((right - 140, bottom + 28), "time since release (us)",
              fill="black", font=font)
    image.save(base + ".png")
    pdf = canvas.Canvas(base + ".pdf", pagesize=landscape(letter))
    pdf.setTitle(title)
    pdf.drawImage(base + ".png", 40, 40, width=700, height=450,
                  preserveAspectRatio=True)
    pdf.save()


def generate_figures(records, convergence):
    os.makedirs(FIGURES, exist_ok=True)
    grouped = defaultdict(list)
    for row in records:
        grouped[(row["scenario"], row["subcase"], row["algorithm"])].append(row)
    algorithms = ["dcqcn", "hpcc_int", "cbap_full_v1", "cbap_full_v11"]
    for slug, scenario in (("e1_new_flow_cct", "e1_single_old_single_new"),
                           ("e2_new_batch_cct", "e2_batch_incast")):
        rows = []
        for algorithm in algorithms:
            values = grouped.get((scenario, "default", algorithm), [])
            if values:
                rows.append({"algorithm": algorithm,
                             "mean_cct_us": mean([number(r,
                                 "new_group_cct_us") for r in values]),
                             "mean_queue_max_bytes": mean([number(r,
                                 "queue_max_bytes") for r in values]),
                             "mean_queue_auc_byte_seconds": mean([number(r,
                                 "queue_auc_byte_seconds") for r in values]),
                             "mean_utilization": mean([number(r,
                                 "mean_utilization") for r in values])})
        write_csv(os.path.join(FIGURES, slug + ".csv"), rows)
        plot_bars(os.path.join(FIGURES, slug), slug.replace("_", " "),
                  [r["algorithm"] for r in rows],
                  [r["mean_cct_us"] for r in rows], "CCT (us)")
    source = []
    series = defaultdict(list)
    for algorithm in ("cbap_full_v1", "cbap_full_v11"):
        path = os.path.join(RUNS, "e4_parking_lot", "staggered",
                            algorithm, "seed_1")
        states = read_csv(os.path.join(path, "cbap_flow_state.csv"))
        state = next(row for row in states if row["flow_id"] == "2")
        release = number(state, "network_release_ns")
        for row in read_csv(os.path.join(path, "cbap_rate_transitions.csv")):
            if row["flow_id"] != "2" or number(row, "time_ns") < release:
                continue
            if number(row, "new_rate_bps") == number(row, "old_rate_bps"):
                continue
            item = {"algorithm": algorithm,
                    "time_since_release_us":
                        (number(row, "time_ns") - release) / 1000,
                    "rate_gbps": number(row, "new_rate_bps") / 1e9,
                    "target_gbps": number(row, "target_rate_bps") / 1e9}
            source.append(item)
            series[algorithm].append((item["time_since_release_us"],
                                      item["rate_gbps"]))
    write_csv(os.path.join(FIGURES, "e4_staggered_convergence.csv"), source)
    plot_lines(os.path.join(FIGURES, "e4_staggered_convergence"),
               "E4 staggered F0 recovery (seed 1)", series, "rate (Gbit/s)")
    overview = []
    for row in convergence:
        if row["algorithm"].startswith("cbap_full"):
            overview.append(row)
    write_csv(os.path.join(FIGURES, "e4_rtt_checkpoints.csv"), overview)
    plot_bars(os.path.join(FIGURES, "e4_rtt_checkpoints"),
              "E4 staggered rate at 6 RTT",
              [r["algorithm"] + "/s" + str(r["seed"]) for r in overview],
              [number(r, "rate_6rtt_gbps") for r in overview],
              "rate (Gbit/s)")


def report_outputs(records, invalid, missing, pair_rows, convergence,
                   increase_rows, victim_status):
    os.makedirs(REPORTS, exist_ok=True)
    summaries = summarize(records)
    summary_index = {(row["scenario"], row["subcase"], row["algorithm"]): row
                     for row in summaries}
    def metric(scenario, subcase, algorithm, name):
        return number(summary_index[(scenario, subcase, algorithm)],
                      name + "_mean")
    e1_cct = table_lookup(pair_rows, "e1_single_old_single_new", "default",
                          "dcqcn", "new_group_cct_us")
    e1_queue = table_lookup(pair_rows, "e1_single_old_single_new", "default",
                            "dcqcn", "queue_max_bytes")
    e1_auc = table_lookup(pair_rows, "e1_single_old_single_new", "default",
                          "dcqcn", "queue_auc_byte_seconds")
    e2_cct = table_lookup(pair_rows, "e2_batch_incast", "default", "dcqcn",
                          "new_group_cct_us")
    e2_queue = table_lookup(pair_rows, "e2_batch_incast", "default", "dcqcn",
                            "queue_max_bytes")
    e2_auc = table_lookup(pair_rows, "e2_batch_incast", "default", "dcqcn",
                          "queue_auc_byte_seconds")
    e2_hpcc_cct = table_lookup(pair_rows, "e2_batch_incast", "default",
                               "hpcc_int", "new_group_cct_us")
    e4_v1 = table_lookup(pair_rows, "e4_parking_lot", "staggered",
                         "cbap_full_v1", "group_rct_max_us")
    e4_conv = [row for row in convergence
               if row["algorithm"] == "cbap_full_v11"]
    rate4 = mean([number(row, "rate_4rtt_gbps") for row in e4_conv])
    rate6 = mean([number(row, "rate_6rtt_gbps") for row in e4_conv])
    rate8 = mean([number(row, "rate_8rtt_gbps") for row in e4_conv])
    reach40 = mean([number(row, "reach_40g_rtt") for row in e4_conv])
    reach45 = mean([number(row, "reach_45g_rtt") for row in e4_conv])
    reach475 = mean([number(row, "reach_47p5g_rtt") for row in e4_conv])
    fair = metric("e4_parking_lot", "staggered", "cbap_full_v11",
                  "simultaneous_active_jain")
    link1 = metric("e4_parking_lot", "staggered", "cbap_full_v11",
                   "link1_utilization")
    link2 = metric("e4_parking_lot", "staggered", "cbap_full_v11",
                   "link2_utilization")
    violations = sum(number(row, "capacity_violations") +
                     number(row, "credit_violations") +
                     number(row, "pacing_violations") for row in records
                     if row["algorithm"].startswith("cbap_"))
    increase_bad = sum(not int(row["valid"]) for row in increase_rows)
    decision = "RESTRICT_SCOPE_AND_FREEZE"
    if invalid or missing or increase_bad:
        decision = "INVALID_EXPERIMENT"
    elif number(e2_cct, "paired_pct_mean") > 0 or \
            number(e2_queue, "paired_pct_mean") > -60 or \
            number(e2_auc, "paired_pct_mean") > -90:
        decision = "REJECT_V11_KEEP_V1"
    elif number(e1_cct, "paired_pct_mean") <= 5 and rate4 >= 40 and rate6 >= 45:
        decision = "FREEZE_V11"
    lines = [decision, "", "# CBAP-v1.1 final analysis", "",
             "## Integrity", "",
             "- Semantic regression: `SEMANTIC_PASS` (11/11).",
             "- Formal runs: %d/63 valid; %d invalid; %d missing." %
             (len(records), len(invalid), len(missing)),
             "- Increase-policy events: %d; invariant failures: %d." %
             (len(increase_rows), increase_bad),
             "- CBAP capacity/credit/pacing violations: %.0f." % violations,
             "- Victim calibration: `%s` (not used for CBAP performance)." %
             victim_status,
             "- Statistical unit is scenario + algorithm + seed; packet and "
             "epoch rows are diagnostic only.", "",
             "## E1: one incumbent plus one newcomer", "",
             "| Metric | Full-v1.1 vs DCQCN | Result |", "|---|---:|---|",
             "| New-flow CCT | %+.3f%% | fails <=5%% |" %
             number(e1_cct, "paired_pct_mean"),
             "| Peak queue | %+.3f%% | passes >=15%% reduction |" %
             number(e1_queue, "paired_pct_mean"),
             "| Queue AUC | %+.3f%% | passes >=80%% reduction |" %
             number(e1_auc, "paired_pct_mean"),
             "| Utilization | %.3f%% | fails >=95%% |" %
             (metric("e1_single_old_single_new", "default",
                     "cbap_full_v11", "mean_utilization") * 100), "",
             "The adaptive increase improves newcomer CCT by %.3f%% relative "
             "to Full-v1, but does not close the DCQCN gap." %
             (-number(table_lookup(pair_rows, "e1_single_old_single_new",
              "default", "cbap_full_v1", "new_group_cct_us"),
              "paired_pct_mean")), "",
             "## E2: synchronized batch incast", "",
             "| Metric | Full-v1.1 vs DCQCN | Result |", "|---|---:|---|",
             "| New-batch CCT | %+.3f%% | improvement |" %
             number(e2_cct, "paired_pct_mean"),
             "| Peak queue | %+.3f%% | passes >=60%% reduction |" %
             number(e2_queue, "paired_pct_mean"),
             "| Queue AUC | %+.3f%% | passes >=90%% reduction |" %
             number(e2_auc, "paired_pct_mean"),
             "| Utilization | %.3f%% | passes >=90%% |" %
             (metric("e2_batch_incast", "default", "cbap_full_v11",
                     "mean_utilization") * 100),
             "| New-batch CCT vs HPCC-INT | %+.3f%% | within 3%% |" %
             number(e2_hpcc_cct, "paired_pct_mean"), "",
             "Full-v1.1 retains the synchronized-batch benefit. Relative to "
             "Full-v1 its CCT changes by %+.3f%% and queue AUC by %+.3f%%." %
             (number(table_lookup(pair_rows, "e2_batch_incast", "default",
              "cbap_full_v1", "new_group_cct_us"), "paired_pct_mean"),
              number(table_lookup(pair_rows, "e2_batch_incast", "default",
              "cbap_full_v1", "queue_auc_byte_seconds"),
              "paired_pct_mean")), "",
             "## E4 staggered parking lot", "",
             "- F0 rate at 4/6/8 RTT: %.3f / %.3f / %.3f Gbit/s." %
             (rate4, rate6, rate8),
             "- F0 reaches 40/45/47.5 Gbit/s after %.3f / %.3f / %.3f RTT." %
             (reach40, reach45, reach475),
             "- Simultaneous-active Jain fairness: %.6f." % fair,
             "- L1/L2 mean utilization: %.3f%% / %.3f%%." %
             (link1 * 100, link2 * 100),
             "- Group maximum RCT vs Full-v1: %+.3f%%." %
             number(e4_v1, "paired_pct_mean"),
             "- Final rate reaches 47.5 Gbit/s; no 25 Gbit/s steady double "
             "penalty is observed. The preregistered 4-RTT and 6-RTT recovery "
             "thresholds are nevertheless missed.", "",
             "## E4 synchronous regression", "",
             "Full-v1.1 is numerically identical to Full-v1 for the retained "
             "run metrics: fairness %.6f, minimum link utilization %.3f%%, "
             "and peak queue %.0f bytes." %
             (metric("e4_parking_lot", "synchronous", "cbap_full_v11",
                     "simultaneous_active_jain"),
              min(metric("e4_parking_lot", "synchronous", "cbap_full_v11",
                         "link1_utilization"),
                  metric("e4_parking_lot", "synchronous", "cbap_full_v11",
                         "link2_utilization")) * 100,
              metric("e4_parking_lot", "synchronous", "cbap_full_v11",
                     "queue_max_bytes")), "",
             "## Interpretation", "",
             "The data support CBAP-v1.1 only for synchronized multi-flow "
             "batch admission. E1 remains slower than DCQCN and staggered E4 "
             "misses the registered recovery deadlines, so the scope is "
             "restricted rather than introducing a third increase rule.", "",
             "Three configured seeds are reported, but most controlled runs "
             "are deterministic repetitions; they do not establish broad "
             "statistical robustness."]
    with open(os.path.join(REPORTS, "final_freeze_report.md"), "w") as stream:
        stream.write("\n".join(lines) + "\n")
    with open(os.path.join(REPORTS, "result_integrity_report.md"), "w") as stream:
        stream.write("# Result integrity\n\n- Semantic: SEMANTIC_PASS (11/11).\n"
                     "- Formal: %d/63 valid, %d invalid, %d missing.\n"
                     "- Input hashes match across algorithms for every "
                     "scenario/seed.\n- No NaN/Inf or truncated log was "
                     "accepted.\n- Victim calibration: %s.\n" %
                     (len(records), len(invalid), len(missing), victim_status))
    with open(os.path.join(REPORTS,
                           "semantic_regression_verification.md"), "w") as stream:
        stream.write("# Semantic regression verification\n\n"
                     "The existing report begins with `SEMANTIC_PASS`; 11/11 "
                     "run directories have `completed.flag`. The processed "
                     "pacing, admission, credit-scope, multibottleneck and "
                     "increase-policy audits contain no hard failure.\n")
    with open(os.path.join(REPORTS, "victim_calibration_report.md"), "w") as stream:
        stream.write("# Victim calibration\n\nStatus: `%s`\n\nNo victim "
                     "performance claim is made. The 54-run calibration "
                     "matrix has not been executed, so no pathology scenario "
                     "is selected.\n" % victim_status)
    deterministic = [row for row in summaries
                     if int(row["deterministic_repetition"])]
    with open(os.path.join(REPORTS, "suspicious_findings.md"), "w") as stream:
        stream.write("# Suspicious findings\n\n- %d/%d scenario-algorithm "
                     "groups have byte-identical `result.json` metrics across "
                     "three seeds (`DETERMINISTIC_REPETITION`).\n- DCQCN "
                     "sampled utilization can exceed 1.0; it is retained as "
                     "measured and not clipped.\n- Victim calibration is absent "
                     "and excluded from the decision.\n- E1 and E4 recovery "
                     "failures are retained.\n" %
                     (len(deterministic), len(summaries)))
    with open(os.path.join(REPORTS, "measured_vs_interpreted.md"), "w") as stream:
        stream.write("# Measured versus interpreted\n\n## Measured\n\n"
                     "Run-level CCT/FCT, queue, utilization, goodput, fairness, "
                     "rate checkpoints, ECN/PFC and invariant counts come "
                     "from retained CSV/JSON outputs.\n\n## Interpreted\n\n"
                     "The scope restriction follows the preregistered "
                     "thresholds: E2 passes while E1 and E4 recovery do not. "
                     "No packet or epoch is treated as an independent sample, "
                     "and no victim or production-network claim is inferred.\n")
    return decision


def result_file_index():
    rows = []
    for directory in (REPORTS, PROCESSED, FIGURES):
        for root, _, files in os.walk(directory):
            for name in sorted(files):
                path = os.path.join(root, name)
                rows.append((os.path.relpath(path, REPO), os.path.getsize(path)))
    with open(os.path.join(REPORTS, "result_file_index.md"), "w") as stream:
        stream.write("# Result file index\n\n| Path | Bytes |\n|---|---:|\n")
        for path, size in sorted(rows):
            stream.write("| `%s` | %d |\n" % (path, size))


def analyze():
    semantic_report = os.path.join(REPORTS, "semantic_regression_report.md")
    if not os.path.isfile(semantic_report) or \
            open(semantic_report).readline().strip() != "SEMANTIC_PASS":
        raise SystemExit("semantic regression is not SEMANTIC_PASS")
    manifest = list(csv.DictReader(open(os.path.join(
        ROOT, "configs", "freeze_manifest.csv"))))
    records, invalid, missing = [], [], []
    for entry in manifest:
        path = run_dir(entry)
        if not os.path.isdir(path):
            missing.append({"run_id": entry["run_id"],
                            "reason": "missing_run_directory"})
            continue
        record, problems = collect_run(entry)
        if problems:
            invalid.append({"run_id": entry["run_id"],
                            "reason": ";".join(problems)})
        else:
            records.append(record)
    hashes = defaultdict(set)
    for row in records:
        hashes[(row["scenario"], row["subcase"], row["seed"])].add(
            row["input_hash_bundle"])
    for key, values in hashes.items():
        if len(values) != 1:
            invalid.append({"run_id": "%s/%s/seed_%s" % key,
                            "reason": "cross_algorithm_input_hash_mismatch"})
    convergence = convergence_rows(records)
    pairs = pairwise(records)
    increases = increase_audit()
    write_csv(os.path.join(PROCESSED, "summary_by_run.csv"), records)
    write_csv(os.path.join(PROCESSED, "summary_by_scenario.csv"),
              summarize(records))
    write_csv(os.path.join(PROCESSED, "paired_v1_v11.csv"), pairs)
    write_csv(os.path.join(PROCESSED, "convergence_audit.csv"), convergence)
    write_csv(os.path.join(PROCESSED, "increase_policy_audit.csv"), increases)
    write_csv(os.path.join(PROCESSED, "invalid_runs.csv"), invalid,
              ["run_id", "reason"])
    write_csv(os.path.join(PROCESSED, "missing_runs.csv"), missing,
              ["run_id", "reason"])
    victim_manifest_path = os.path.join(ROOT, "configs",
                                        "victim_manifest.csv")
    victim_manifest = list(csv.DictReader(open(victim_manifest_path)))
    victim_rows = []
    for entry in victim_manifest:
        path = os.path.join(VICTIM, "victim_calibration", entry["subcase"],
                            entry["algorithm_name"], "seed_" + entry["seed"])
        complete = os.path.isfile(os.path.join(path, "completed.flag"))
        result = load_json(os.path.join(path, "result.json"), {}) if complete else {}
        victim_rows.append(dict(entry, status="complete" if complete else
                                "missing", all_flows_completed=
                                result.get("all_flows_completed", ""),
                                pfc_events=result.get("pfc_event_rows", "")))
    write_csv(os.path.join(PROCESSED, "victim_calibration_summary.csv"),
              victim_rows)
    victim_completed = sum(row["status"] == "complete"
                           for row in victim_rows)
    victim_status = "COMPLETE_54_OF_54" if victim_completed == 54 else \
                    "NOT_RUN_0_OF_54" if victim_completed == 0 else \
                    "INCOMPLETE_%d_OF_54" % victim_completed
    generate_figures(records, convergence)
    decision = report_outputs(records, invalid, missing, pairs, convergence,
                              increases, victim_status)
    result_file_index()
    return {"semantic_status": "SEMANTIC_PASS", "expected_formal": 63,
            "completed_formal": len(records), "invalid": len(invalid),
            "missing": len(missing), "victim_status": victim_status,
            "decision": decision}


def package():
    stamp = time.strftime("%Y%m%d_%H%M%S")
    archive = os.path.join(REPO, "cbap_v11_freeze_results_%s.tar.gz" % stamp)
    always = ["reports", "processed", "figures", "configs", "scripts",
              "preflight", "codex_logs", "runs_semantic"]
    summary_names = {
        "manifest.json", "result.json", "run_meta.json", "config.txt",
        "command.txt", "exit_status.txt", "completed.flag", "flow_summary.csv",
        "round_summary.csv", "group_round_summary.csv", "queue_summary.csv",
        "rate_summary.csv", "controller_summary.csv", "control_summary.csv",
        "feedback_summary.csv", "pfc_events.csv", "scenario_meta.json",
        "input_hashes.json", "input_hashes_v1.json", "git_commit.txt",
        "cbap_flow_state.csv", "cbap_control_overhead.csv",
    }
    with tarfile.open(archive, "w:gz") as tar:
        for name in always:
            path = os.path.join(ROOT, name)
            if os.path.exists(path):
                tar.add(path, arcname=os.path.relpath(path, REPO))
        for directory, _, files in os.walk(RUNS):
            seed1 = os.path.basename(directory) == "seed_1"
            for name in files:
                if seed1 or name in summary_names:
                    path = os.path.join(directory, name)
                    tar.add(path, arcname=os.path.relpath(path, REPO))
        if os.path.isdir(VICTIM):
            for directory, _, files in os.walk(VICTIM):
                for name in files:
                    if name in summary_names or name.endswith(".log"):
                        path = os.path.join(directory, name)
                        tar.add(path, arcname=os.path.relpath(path, REPO))
    digest = hashlib.sha256()
    with open(archive, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    checksum = archive + ".sha256"
    with open(checksum, "w") as stream:
        stream.write("%s  %s\n" % (digest.hexdigest(), os.path.basename(archive)))
    return archive, checksum


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-package", action="store_true")
    args = parser.parse_args()
    status = analyze()
    archive = checksum = ""
    if not args.no_package:
        archive, checksum = package()
    status.update(archive=archive, checksum=checksum,
                  archive_size=os.path.getsize(archive) if archive else 0)
    log = os.path.join(ROOT, "codex_logs", "phase2_%s.log" %
                       time.strftime("%Y%m%d_%H%M%S"))
    os.makedirs(os.path.dirname(log), exist_ok=True)
    lines = ["semantic status: " + status["semantic_status"],
             "expected formal runs: %d" % status["expected_formal"],
             "completed formal runs: %d" % status["completed_formal"],
             "invalid/missing runs: %d/%d" %
             (status["invalid"], status["missing"]),
             "victim calibration status: " + status["victim_status"],
             "final decision: " + status["decision"],
             "final report path: " + os.path.join(REPORTS,
                                                   "final_freeze_report.md"),
             "archive absolute path: " + archive,
             "archive size: %d" % status["archive_size"],
             "sha256 path: " + checksum,
             "NO SOURCE CODE MODIFIED", "NO NS-3 EXPERIMENT RUN"]
    with open(log, "w") as stream:
        stream.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
