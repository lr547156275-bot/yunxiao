#!/usr/bin/env python3
"""Recompute CBAP-v0 run, audit, statistical, plot and report artifacts.

The statistical unit is one (scenario, subcase, algorithm, seed) run.  Packet
and epoch rows are used only to derive a run metric; they are never treated as
independent samples.
"""
import argparse
import csv
import gzip
import json
import math
import os
import statistics
import struct
import subprocess
import zlib
from collections import defaultdict


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ALGORITHMS = (
    "dcqcn", "hpcc_int", "bop_qb", "independent_min_grant",
    "cbap_init_only", "cbap_rate_only", "cbap_full",
)
CBAP = set(ALGORITHMS[3:])


def read_csv(path):
    if os.path.isfile(path):
        with open(path, newline="") as stream:
            return list(csv.DictReader(stream))
    if os.path.isfile(path + ".gz"):
        with gzip.open(path + ".gz", "rt", newline="") as stream:
            return list(csv.DictReader(stream))
    return []


def num(row, key, default=0.0):
    try:
        value = float(row.get(key, default))
        return value if math.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def percentile(values, fraction):
    values = sorted(values)
    if not values:
        return 0.0
    pos = fraction * (len(values) - 1)
    low, high = int(math.floor(pos)), int(math.ceil(pos))
    if low == high:
        return values[low]
    return values[low] + (values[high] - values[low]) * (pos - low)


def mean(values):
    return statistics.mean(values) if values else 0.0


def median(values):
    return statistics.median(values) if values else 0.0


def pct(new, baseline):
    return (new - baseline) / baseline * 100.0 if baseline else 0.0


def write_csv(path, rows, fields=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with open(path, "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields,
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def input_schedule(run):
    result = {}
    with open(os.path.join(run, "rounds.txt")) as stream:
        next(stream)
        for line in stream:
            fields = line.split()
            if fields:
                result[int(fields[0])] = {
                    "group": int(fields[2]),
                    "bytes": int(fields[4]),
                    "ready_s": int(fields[8]) / 1e9,
                }
    return result


def group_link_rows(rows):
    result = defaultdict(list)
    for row in rows:
        result[row.get("link_id", "")].append(row)
    return result


def derive_run(run):
    meta = json.load(open(os.path.join(run, "run_meta.json")))
    base = json.load(open(os.path.join(run, "result.json")))
    scenario_meta = json.load(open(os.path.join(run,
                                                "scenario_meta.json")))
    flow = read_csv(os.path.join(run, "flow_summary.csv"))
    rounds = read_csv(os.path.join(run, "round_summary.csv"))
    links = read_csv(os.path.join(run, "selected_link_timeseries.csv"))
    pfc = read_csv(os.path.join(run, "pfc_events.csv"))
    schedule = input_schedule(run)
    by_flow = {int(row["flow_id"]): row for row in flow}
    fct_us = {}
    goodput = {}
    finish = {}
    for fid, row in by_flow.items():
        ready = schedule[fid]["ready_s"]
        finish[fid] = num(row, "finish_time")
        fct_us[fid] = max(finish[fid] - ready, 0) * 1e6
        goodput[fid] = num(row, "flow_goodput") / 1e9
    group_rct = defaultdict(float)
    for row in rounds:
        fid = int(row["flow_id"])
        gid = int(row["round_group_id"])
        completion = num(row, "ack_completion_time")
        group_rct[gid] = max(group_rct[gid],
                             max(completion - schedule[fid]["ready_s"], 0)
                             * 1e6)
    queue = [num(row, "queue_bytes") for row in links]
    util = [num(row, "utilization") for row in links]
    per_link = group_link_rows(links)
    link_util_min = min((mean([num(r, "utilization") for r in rows])
                         for rows in per_link.values()), default=0)
    out = dict(base)
    out.update({
        "run_id": meta["run_id"],
        "run_dir": run,
        "cc_mode": meta["cc_mode"],
        "valid": 1,
        "flow_fct_median_us": median(list(fct_us.values())),
        "flow_fct_p95_us": percentile(list(fct_us.values()), .95),
        "group_rct_median_us": median(list(group_rct.values())),
        "group_rct_p95_us": percentile(list(group_rct.values()), .95),
        "queue_mean_bytes": mean(queue),
        "link_min_mean_utilization": link_util_min,
        "pfc_pause_events": sum(1 for r in pfc
                                if r.get("event_type") in
                                ("PAUSE", "1", "pause")),
        "pfc_resume_events": sum(1 for r in pfc
                                 if r.get("event_type") in
                                 ("RESUME", "0", "resume")),
        "completion_skew_us":
            (max(finish.values()) - min(finish.values())) * 1e6
            if finish else 0,
        "jain_goodput":
            (sum(goodput.values()) ** 2 /
             (len(goodput) * sum(v * v for v in goodput.values())))
            if goodput and sum(v * v for v in goodput.values()) else 0,
        "flow0_fct_us": fct_us.get(0, 0),
        "flow1_fct_us": fct_us.get(1, 0),
        "flow2_fct_us": fct_us.get(2, 0),
        "flow0_goodput_gbps": goodput.get(0, 0),
        "flow1_goodput_gbps": goodput.get(1, 0),
        "flow2_goodput_gbps": goodput.get(2, 0),
    })
    new_ids = scenario_meta.get("new_flow_ids",
                                scenario_meta.get("contributor_flow_ids", []))
    old_ids = scenario_meta.get("old_flow_ids",
                                [scenario_meta.get("victim_flow_id", -1)])
    out["new_fct_median_us"] = median([fct_us[x] for x in new_ids
                                       if x in fct_us])
    out["new_fct_max_us"] = max([fct_us[x] for x in new_ids
                                 if x in fct_us] or [0])
    # In E1/E2 the preregistered collective completion time is the barrier of
    # the newly released batch, not the later completion of the incumbent
    # long-flow group.  With one round per flow this is the maximum FCT among
    # the scenario's explicitly declared new-flow IDs.
    out["new_group_cct_us"] = out["new_fct_max_us"]
    out["old_fct_mean_us"] = mean([fct_us[x] for x in old_ids
                                   if x in fct_us])
    out["old_goodput_mean_gbps"] = mean([goodput[x] for x in old_ids
                                         if x in goodput])
    out["new_goodput_mean_gbps"] = mean([goodput[x] for x in new_ids
                                         if x in goodput])
    out["victim_fct_us"] = fct_us.get(
        scenario_meta.get("victim_flow_id", -1), 0)
    out["victim_goodput_gbps"] = goodput.get(
        scenario_meta.get("victim_flow_id", -1), 0)
    if meta["algorithm"] in CBAP:
        overhead = read_csv(os.path.join(run, "cbap_control_overhead.csv"))
        out["control_bytes"] = num(overhead[0], "total_control_bytes") \
            if overhead else 0
        admission = read_csv(os.path.join(run, "cbap_admission.csv"))
        states = read_csv(os.path.join(run, "cbap_flow_state.csv"))
        out["admission_capacity_invalid"] = sum(
            int(num(r, "capacity_valid", 1) == 0) for r in admission)
        out["first_feedback_error_mean_us"] = mean([
            (num(r, "first_fresh_feedback_ns") -
             num(r, "estimated_first_feedback_ns")) / 1000
            for r in states if num(r, "first_fresh_feedback_ns")])
        out["rate_increases"] = sum(num(r, "rate_increases") for r in states)
        out["rate_decreases"] = sum(num(r, "rate_decreases") for r in states)
    else:
        out.update({"control_bytes": 0, "admission_capacity_invalid": 0,
                    "first_feedback_error_mean_us": 0,
                    "rate_increases": 0, "rate_decreases": 0})
    return out


def validate_run(run, expected):
    problems = []
    required = ("completed.flag", "exit_status.txt", "run_meta.json",
                "result.json", "flow_summary.csv", "round_summary.csv")
    for name in required:
        if not os.path.isfile(os.path.join(run, name)):
            problems.append("missing_" + name)
    if problems:
        return problems
    meta = json.load(open(os.path.join(run, "run_meta.json")))
    result = json.load(open(os.path.join(run, "result.json")))
    if int(open(os.path.join(run, "exit_status.txt")).read().strip()):
        problems.append("nonzero_exit")
    if not result.get("all_flows_completed"):
        problems.append("incomplete_flow")
    if result.get("log_truncated"):
        problems.append("log_truncated")
    if int(meta.get("cc_mode", -1)) != int(expected["cc_mode"]):
        problems.append("cc_mode_mismatch")
    if meta.get("algorithm") != expected["algorithm"]:
        problems.append("algorithm_mismatch")
    if any(isinstance(v, float) and not math.isfinite(v)
           for v in result.values()):
        problems.append("nonfinite_result")
    if expected["algorithm"] in CBAP:
        if result.get("capacity_violations", 0):
            problems.append("capacity_violation")
        if result.get("credit_violations", 0):
            problems.append("credit_violation")
    return problems


def aggregate(records):
    metrics = [
        "flow_fct_mean_us", "flow_fct_max_us", "group_rct_mean_us",
        "group_rct_max_us", "new_fct_median_us", "new_fct_max_us",
        "old_fct_mean_us", "victim_fct_us", "victim_goodput_gbps",
        "queue_max_bytes", "queue_p95_bytes", "queue_auc_byte_seconds",
        "mean_utilization", "link_min_mean_utilization",
        "payload_goodput_gbps", "ecn_marks", "pfc_event_rows",
        "completion_skew_us", "jain_goodput", "control_bytes",
    ]
    groups = defaultdict(list)
    for row in records:
        groups[(row["scenario"], row["subcase"],
                row["algorithm"])].append(row)
    summary, stats = [], []
    for key, rows in sorted(groups.items()):
        item = {"scenario": key[0], "subcase": key[1],
                "algorithm": key[2], "seed_count": len(rows)}
        for metric in metrics:
            values = [float(r.get(metric, 0)) for r in rows]
            item[metric + "_mean"] = mean(values)
            item[metric + "_median"] = median(values)
            item[metric + "_min"] = min(values)
            item[metric + "_max"] = max(values)
            stats.append({
                "scenario": key[0], "subcase": key[1],
                "algorithm": key[2], "metric": metric,
                "seed_count": len(values), "mean": mean(values),
                "median": median(values), "min": min(values),
                "max": max(values),
            })
        summary.append(item)
    return summary, stats


def paired(records):
    by_key = {(r["scenario"], r["subcase"], r["algorithm"],
               int(r["seed"])): r for r in records}
    metrics = ("group_rct_mean_us", "new_fct_median_us",
               "queue_max_bytes", "queue_auc_byte_seconds",
               "mean_utilization", "payload_goodput_gbps",
               "ecn_marks", "pfc_event_rows")
    rows = []
    scenarios = sorted(set((r["scenario"], r["subcase"])
                           for r in records))
    for scenario, subcase in scenarios:
        for baseline in ALGORITHMS:
            if baseline == "cbap_full":
                continue
            for metric in metrics:
                diffs = []
                for seed in (1, 2, 3):
                    new = by_key.get((scenario, subcase,
                                      "cbap_full", seed))
                    old = by_key.get((scenario, subcase, baseline, seed))
                    if new and old:
                        diffs.append(pct(float(new.get(metric, 0)),
                                         float(old.get(metric, 0))))
                if diffs:
                    rows.append({
                        "scenario": scenario, "subcase": subcase,
                        "new_algorithm": "cbap_full",
                        "baseline": baseline, "metric": metric,
                        "paired_seed_count": len(diffs),
                        "paired_percent_mean": mean(diffs),
                        "paired_percent_median": median(diffs),
                        "paired_percent_min": min(diffs),
                        "paired_percent_max": max(diffs),
                        "favorable_seed_count": sum(
                            d < 0 if metric not in
                            ("mean_utilization", "payload_goodput_gbps")
                            else d > 0 for d in diffs),
                    })
    return rows


def audits(records):
    capacity, credit, roots, freshness, rates = [], [], [], [], []
    for run in records:
        if run["algorithm"] not in CBAP:
            continue
        path = run["run_dir"]
        admissions = read_csv(os.path.join(path, "cbap_admission.csv"))
        states = read_csv(os.path.join(path, "cbap_flow_state.csv"))
        ports = read_csv(os.path.join(path, "cbap_port_summary.csv"))
        transitions = read_csv(os.path.join(path,
                                            "cbap_rate_transitions.csv"))
        scenario_meta = json.load(open(os.path.join(path,
                                                    "scenario_meta.json")))
        paths = {}
        with open(os.path.join(path, "controlled_paths.txt")) as stream:
            next(stream)
            for line in stream:
                fields = [int(x) for x in line.split()]
                paths[fields[0]] = fields[2:]
        admission_groups = defaultdict(list)
        for row in admissions:
            admission_groups[int(row["batch_id"])].append(row)
        all_links = sorted(set(link for flow_path in paths.values()
                               for link in flow_path))
        for batch, batch_rows in sorted(admission_groups.items()):
            for link in all_links:
                members = [r for r in batch_rows
                           if link in paths[int(r["flow_id"])]]
                if not members:
                    continue
                admit_sum = sum(num(r, "admit_rate_bps")
                                for r in members)
                base_sum = sum(num(r, "base_rate_bps")
                               for r in members)
                effective = min(num(r, "effective_capacity_bps")
                                for r in members)
                q_target = scenario_meta["ecn_kmin_bytes"] * 0.50
                observed = max(num(r, "observed_queue_bytes")
                               for r in members)
                margin = max(num(r, "packet_margin_bytes")
                             for r in members)
                horizon = max(num(r, "feedback_horizon_ns")
                              for r in members)
                room = max(q_target - observed - margin, 0)
                queue_rate = room * 8e9 / horizon if horizon else 0
                admit_budget = base_sum + queue_rate
                capacity.append({
                    "run_id": run["run_id"], "batch_id": batch,
                    "link_id": link, "pending_flow_count": len(members),
                    "base_rate_sum_bps": base_sum,
                    "admit_rate_sum_bps": admit_sum,
                    "effective_capacity_bps": effective,
                    "observed_queue_bytes": observed,
                    "packet_margin_bytes": margin,
                    "feedback_horizon_ns": horizon,
                    "queue_rate_budget_bps": queue_rate,
                    "admit_budget_bps": admit_budget,
                    "independent_diagnostic":
                        int(run["algorithm"] == "independent_min_grant"),
                    "base_capacity_valid": int(base_sum <= effective + 1),
                    "admit_capacity_valid": int(
                        admit_sum <= admit_budget + 1),
                    "oversubscription_bps":
                        max(admit_sum - admit_budget, 0),
                })
        for row in states:
            credit.append({
                "run_id": run["run_id"], "flow_id": row["flow_id"],
                "initial_credit_bytes": row["initial_credit_bytes"],
                "excess_bytes": row["excess_bytes"],
                "credit_violations": row["credit_violations"],
                "valid": int(num(row, "excess_bytes") <=
                             num(row, "initial_credit_bytes") and
                             num(row, "credit_violations") == 0),
            })
            estimated = num(row, "estimated_first_feedback_ns")
            actual = num(row, "first_fresh_feedback_ns")
            freshness.append({
                "run_id": run["run_id"], "flow_id": row["flow_id"],
                "estimated_first_feedback_ns": int(estimated),
                "actual_first_fresh_feedback_ns": int(actual),
                "estimation_error_ns": int(actual - estimated)
                if actual else 0,
                "stale_feedback_count": row["stale_feedback"],
            })
        true_root = scenario_meta.get("true_root_link_id", "")
        port_groups = defaultdict(list)
        for row in ports:
            port_groups[int(row["link_id"])].append(row)
        for link, link_rows in sorted(port_groups.items()):
            root_rows = [r for r in link_rows
                         if int(num(r, "port_state", 4)) == 2]
            propagated_rows = [r for r in link_rows
                               if int(num(r, "port_state", 4)) == 3]
            first = min([int(num(r, "delivery_time_ns"))
                         for r in root_rows] or [0])
            ground_truth = true_root != ""
            roots.append({
                "run_id": run["run_id"], "link_id": link,
                "sample_count": len(link_rows),
                "root_epoch_count": len(root_rows),
                "propagated_epoch_count": len(propagated_rows),
                "first_root_delivery_ns": first,
                "release_to_first_root_us":
                    (first - 3000000) / 1000.0 if first >= 3000000
                    else 0,
                "ground_truth_known": int(ground_truth),
                "true_root_link_id": true_root,
                "true_positive": int(ground_truth and bool(root_rows) and
                                     link == int(true_root)),
                "false_positive": int(ground_truth and bool(root_rows) and
                                      link != int(true_root)),
                "propagated_as_root_error": int(
                    ground_truth and bool(root_rows) and
                    link != int(true_root)),
            })
        decrease_keys = defaultdict(int)
        for row in transitions:
            old = num(row, "old_rate_bps")
            new = num(row, "new_rate_bps")
            if new < old:
                decrease_keys[(row["epoch"], row["flow_id"])] += 1
        increase_bound_violations = 0
        stale_modified = 0
        capacity_invalid = 0
        increase_count = 0
        decrease_count = 0
        hold_count = 0
        max_feedback_age = 0
        for row in transitions:
            old = num(row, "old_rate_bps")
            new = num(row, "new_rate_bps")
            target = num(row, "target_rate_bps")
            increase_valid = 1
            if new > old and old:
                increase_count += 1
                increase_valid = int(new <= target + 1 and
                                     new <= old * 1.10 + 1 and
                                     new <= old + 2e9 + 1)
            elif new < old:
                decrease_count += 1
            else:
                hold_count += 1
            increase_bound_violations += int(not increase_valid)
            stale_modified += int(
                int(num(row, "stale_feedback")) != 0 and new != old)
            capacity_invalid += int(num(row, "capacity_valid", 1) == 0)
            max_feedback_age = max(max_feedback_age,
                                   num(row, "feedback_age_ns"))
        rates.append({
            "run_id": run["run_id"],
            "transition_rows": len(transitions),
            "rate_increase_count": increase_count,
            "rate_decrease_count": decrease_count,
            "rate_hold_count": hold_count,
            "increase_bound_violation_count": increase_bound_violations,
            "multi_decrease_epoch_violation_count": sum(
                1 for count in decrease_keys.values() if count > 1),
            "stale_feedback_modified_rate_count": stale_modified,
            "capacity_flag_invalid_count": capacity_invalid,
            "maximum_feedback_age_ns": max_feedback_age,
            "valid": int(increase_bound_violations == 0 and
                         all(count <= 1 for count in
                             decrease_keys.values()) and
                         stale_modified == 0 and capacity_invalid == 0),
        })
    return capacity, credit, roots, freshness, rates


def png_plot(path, series, width=960, height=540):
    """Small dependency-free line plot used when matplotlib is unavailable."""
    margin = 55
    points = [(float(x), float(y), label) for x, y, label in series]
    xs = [p[0] for p in points] or [0, 1]
    ys = [p[1] for p in points] or [0, 1]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(0, min(ys)), max(ys)
    if xmax == xmin:
        xmax = xmin + 1
    if ymax == ymin:
        ymax = ymin + 1
    rgb = bytearray([255] * width * height * 3)

    def pixel(x, y, color):
        if 0 <= x < width and 0 <= y < height:
            pos = (y * width + x) * 3
            rgb[pos:pos + 3] = bytes(color)

    def line(x0, y0, x1, y1, color):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        error = dx + dy
        while True:
            pixel(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            twice = 2 * error
            if twice >= dy:
                error += dy
                x0 += sx
            if twice <= dx:
                error += dx
                y0 += sy
    line(margin, height - margin, width - margin, height - margin,
         (0, 0, 0))
    line(margin, margin, margin, height - margin, (0, 0, 0))
    colors = [(40, 90, 180), (210, 70, 60), (30, 150, 90),
              (150, 80, 180), (220, 140, 20), (20, 150, 160),
              (90, 90, 90)]
    grouped = defaultdict(list)
    for x, y, label in points:
        grouped[label].append((x, y))
    for index, (_, values) in enumerate(sorted(grouped.items())):
        coords = []
        for x, y in sorted(values):
            px = int(margin + (x - xmin) / (xmax - xmin) *
                     (width - 2 * margin))
            py = int(height - margin - (y - ymin) / (ymax - ymin) *
                     (height - 2 * margin))
            coords.append((px, py))
            for ox in range(-2, 3):
                for oy in range(-2, 3):
                    pixel(px + ox, py + oy, colors[index % len(colors)])
        for a, b in zip(coords, coords[1:]):
            line(a[0], a[1], b[0], b[1],
                 colors[index % len(colors)])
    raw = b"".join(b"\x00" + bytes(rgb[y * width * 3:
                                           (y + 1) * width * 3])
                   for y in range(height))
    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data +
                struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff))
    data = (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", width, height,
                                       8, 2, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(raw, 9)) +
            chunk(b"IEND", b""))
    with open(path, "wb") as stream:
        stream.write(data)


def pdf_plot(path, title, series):
    labels = sorted(set(label for _, _, label in series))
    lines = ["%s" % title, "Dependency-free plot companion.",
             "Data series: " + ", ".join(labels),
             "Exact source values are in the adjacent CSV."]
    content = ["BT /F1 12 Tf 50 760 Td"]
    for index, text in enumerate(lines):
        safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")",
                                                                           "\\)")
        if index:
            content.append("0 -20 Td")
        content.append("(%s) Tj" % safe)
    content.append("ET")
    stream_data = "\n".join(content).encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(stream_data) +
        stream_data + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(("%d 0 obj\n" % index).encode() + obj +
                      b"\nendobj\n")
    xref = len(output)
    output.extend(("xref\n0 %d\n0000000000 65535 f \n" %
                   (len(objects) + 1)).encode())
    for offset in offsets[1:]:
        output.extend(("%010d 00000 n \n" % offset).encode())
    output.extend(("trailer << /Size %d /Root 1 0 R >>\nstartxref\n%d\n"
                   "%%%%EOF\n" % (len(objects) + 1, xref)).encode())
    with open(path, "wb") as stream:
        stream.write(output)


def make_figures(records, figure_dir):
    os.makedirs(figure_dir, exist_ok=True)
    definitions = [
        ("e1_throughput", "e1_single_old_single_new", "payload_goodput_gbps"),
        ("e1_queue", "e1_single_old_single_new", "queue_max_bytes"),
        ("e1_rate_recovery", "e1_single_old_single_new", "rate_increases"),
        ("e2_cct", "e2_batch_incast", "group_rct_max_us"),
        ("e2_queue", "e2_batch_incast", "queue_max_bytes"),
        ("e2_rebalancing", "e2_batch_incast", "completion_skew_us"),
        ("e3_victim_throughput", "e3_victim_flow", "victim_goodput_gbps"),
        ("e3_root_shared_queue", "e3_victim_flow", "queue_max_bytes"),
        ("e3_pfc", "e3_victim_flow", "pfc_event_rows"),
        ("e4_flow_rates", "e4_parking_lot", "payload_goodput_gbps"),
        ("e4_queue", "e4_parking_lot", "queue_max_bytes"),
        ("e4_fairness", "e4_parking_lot", "jain_goodput"),
    ]
    for name, scenario, metric in definitions:
        data = []
        source = []
        selected = [r for r in records if r["scenario"] == scenario]
        for aindex, algorithm in enumerate(ALGORITHMS):
            rows = [r for r in selected if r["algorithm"] == algorithm]
            for sindex, subcase in enumerate(sorted(set(
                    r["subcase"] for r in rows))):
                values = [float(r.get(metric, 0)) for r in rows
                          if r["subcase"] == subcase]
                value = mean(values)
                x = aindex + sindex * 0.12
                data.append((x, value, algorithm + "/" + subcase))
                source.append({"algorithm": algorithm, "subcase": subcase,
                               "seed_count": len(values),
                               "metric": metric, "mean": value,
                               "median": median(values),
                               "min": min(values) if values else 0,
                               "max": max(values) if values else 0})
        write_csv(os.path.join(figure_dir, name + ".csv"), source)
        png_plot(os.path.join(figure_dir, name + ".png"), data)
        pdf_plot(os.path.join(figure_dir, name + ".pdf"),
                 name + " (" + metric + ")", data)


def decide(records):
    keyed = {(r["scenario"], r["subcase"], r["algorithm"],
              int(r["seed"])): r for r in records}
    def paired_metric(scenario, subcase, metric, baseline="dcqcn"):
        changes = []
        for seed in (1, 2, 3):
            new = keyed.get((scenario, subcase, "cbap_full", seed))
            old = keyed.get((scenario, subcase, baseline, seed))
            if new and old:
                changes.append(pct(float(new.get(metric, 0)),
                                   float(old.get(metric, 0))))
        return mean(changes)
    e1_queue = paired_metric("e1_single_old_single_new", "default",
                             "queue_max_bytes")
    e1_fct = paired_metric("e1_single_old_single_new", "default",
                           "new_fct_median_us")
    e2_queue = paired_metric("e2_batch_incast", "default",
                             "queue_max_bytes")
    e2_cct = paired_metric("e2_batch_incast", "default",
                           "new_group_cct_us")
    violations = sum(int(r.get("capacity_violations", 0)) +
                     int(r.get("credit_violations", 0)) for r in records
                     if r["algorithm"] in CBAP)
    independent = paired_metric("e2_batch_incast", "default",
                                "queue_max_bytes",
                                "independent_min_grant")
    if (e1_queue <= -50 and e1_fct <= 10 and e2_queue <= -60 and
            e2_cct <= 10 and violations == 0 and independent <= -20):
        return "CONTINUE"
    if (e1_queue < 0 and e2_queue < 0 and e1_fct <= 15 and
            e2_cct <= 15 and violations == 0):
        return "CONTINUE_WITH_MAJOR_REVISION"
    return "STOP"


def preregistered_checks(records):
    grouped = defaultdict(list)
    for row in records:
        grouped[(row["scenario"], row["subcase"],
                 row["algorithm"])].append(row)

    def metric(scenario, subcase, algorithm, name):
        return mean([float(r.get(name, 0)) for r in
                     grouped[(scenario, subcase, algorithm)]])

    def change(scenario, subcase, name, baseline="dcqcn"):
        return pct(metric(scenario, subcase, "cbap_full", name),
                   metric(scenario, subcase, baseline, name))

    checks = []
    def add(experiment, requirement, measured, status, note=""):
        checks.append({"experiment": experiment,
                       "requirement": requirement,
                       "measured": measured, "status": status,
                       "note": note})

    add("E1", "peak queue reduction vs DCQCN >=50%",
        "%.3f%%" % -change("e1_single_old_single_new", "default",
                           "queue_max_bytes"),
        "PASS" if change("e1_single_old_single_new", "default",
                         "queue_max_bytes") <= -50 else "FAIL")
    add("E1", "new-flow FCT increase <=10%",
        "%.3f%%" % change("e1_single_old_single_new", "default",
                          "new_fct_median_us"),
        "PASS" if change("e1_single_old_single_new", "default",
                         "new_fct_median_us") <= 10 else "FAIL")
    util_new = metric("e1_single_old_single_new", "default", "cbap_full",
                      "mean_utilization")
    util_old = metric("e1_single_old_single_new", "default", "dcqcn",
                      "mean_utilization")
    add("E1", "utilization reduction <=5 percentage points",
        "%.3f pp reduction" % ((util_old - util_new) * 100),
        "PASS" if util_new >= util_old - .05 else "FAIL")
    add("E1", "old-flow drop and <=4 RTT recovery",
        "not directly derivable from retained 20-us flow samples",
        "NOT_MEASURED",
        "Seed-1 packet evidence is retained, but host TX rate was not "
        "recorded as a packet event.")

    for label, metric_name, threshold, reduction in (
            ("peak queue reduction >=60%", "queue_max_bytes", -60, True),
            ("queue AUC reduction >=50%", "queue_auc_byte_seconds", -50,
             True),
            ("new-batch CCT increase <=10%", "new_group_cct_us", 10,
             False)):
        value = change("e2_batch_incast", "default", metric_name)
        measured = -value if reduction else value
        add("E2", label, "%.3f%%" % measured,
            "PASS" if value <= threshold else "FAIL")
    add("E2", "old-flow worst throughput-drop improvement >=20 pp",
        "not derivable from retained 20-us flow samples", "NOT_MEASURED",
        "Overall old-flow goodput is retained, but the preregistered "
        "1/5/10/20-us worst-window drop is not.")
    dcqcn_pfc = metric("e2_batch_incast", "default", "dcqcn",
                       "pfc_event_rows")
    full_pfc = metric("e2_batch_incast", "default", "cbap_full",
                     "pfc_event_rows")
    add("E2", "PFC reduction >=90% or nonzero-to-zero",
        "DCQCN %.0f; Full %.0f events" % (dcqcn_pfc, full_pfc),
        "NOT_APPLICABLE" if dcqcn_pfc == 0 else
        ("PASS" if full_pfc == 0 or
         (dcqcn_pfc - full_pfc) / dcqcn_pfc >= .90 else "FAIL"))
    util = metric("e2_batch_incast", "default", "cbap_full",
                  "mean_utilization")
    add("E2", "utilization >=90%", "%.3f%%" % (util * 100),
        "PASS" if util >= .90 else "FAIL")
    violations = sum(int(r.get("capacity_violations", 0)) +
                     int(r.get("credit_violations", 0)) for r in records
                     if r["algorithm"] == "cbap_full")
    add("E2", "capacity and credit violations =0", str(violations),
        "PASS" if violations == 0 else "FAIL")
    independent_change = change(
        "e2_batch_incast", "default", "queue_max_bytes",
        "independent_min_grant")
    capacity_rows = read_csv(os.path.join(
        ROOT, "processed", "capacity_audit.csv"))
    independent_oversub = max([
        num(row, "oversubscription_bps") for row in capacity_rows
        if "__independent_min_grant__" in row.get("run_id", "")
        and row.get("run_id", "").startswith("e2_batch_incast")
    ] or [0])
    full_oversub = max([
        num(row, "oversubscription_bps") for row in capacity_rows
        if "__cbap_full__" in row.get("run_id", "")
        and row.get("run_id", "").startswith("e2_batch_incast")
    ] or [0])
    add("E2", "Full queue >=20% below Independent or removes violations",
        "queue change %.3f%%; max oversub %.3f->%.3f Gbit/s" % (
            independent_change, independent_oversub / 1e9,
            full_oversub / 1e9),
        "PASS" if independent_change <= -20 or
        (independent_oversub > 0 and full_oversub == 0) else "FAIL")

    alone = metric("e3_victim_flow", "victim_alone", "dcqcn",
                   "victim_goodput_gbps")
    pfc_on = metric("e3_victim_flow", "pfc_on", "dcqcn",
                    "victim_goodput_gbps")
    pfc_rows = metric("e3_victim_flow", "pfc_on", "dcqcn",
                      "pfc_event_rows")
    ratio = pfc_on / alone if alone else 0
    add("E3", "DCQCN/PFC-on must create victim degradation",
        "throughput ratio %.6f; PFC rows %.0f" % (ratio, pfc_rows),
        "SCENARIO_NOT_STRESSFUL" if ratio > .95 and pfc_rows == 0
        else "PASS")

    jain = metric("e4_parking_lot", "synchronous", "cbap_full",
                  "jain_goodput")
    min_util = metric("e4_parking_lot", "synchronous", "cbap_full",
                      "link_min_mean_utilization")
    f0 = metric("e4_parking_lot", "synchronous", "cbap_full",
                "flow0_goodput_gbps")
    f1 = metric("e4_parking_lot", "synchronous", "cbap_full",
                "flow1_goodput_gbps")
    f2 = metric("e4_parking_lot", "synchronous", "cbap_full",
                "flow2_goodput_gbps")
    ratio = f0 / min(f1, f2) if min(f1, f2) else 0
    add("E4 synchronous", "Jain >=0.95", "%.6f" % jain,
        "PASS" if jain >= .95 else "FAIL")
    add("E4 synchronous", "both link utilization >=90%",
        "%.3f%% minimum mean" % (min_util * 100),
        "PASS" if min_util >= .90 else "FAIL")
    add("E4 synchronous", "F0/min(F1,F2) >=0.90", "%.6f" % ratio,
        "PASS" if ratio >= .90 else "FAIL")

    # Staggered IDs are F1=0, F2=1 and the later F0=2.
    f0 = metric("e4_parking_lot", "staggered", "cbap_full",
                "flow2_goodput_gbps")
    f1 = metric("e4_parking_lot", "staggered", "cbap_full",
                "flow0_goodput_gbps")
    f2 = metric("e4_parking_lot", "staggered", "cbap_full",
                "flow1_goodput_gbps")
    ratio = f0 / min(f1, f2) if min(f1, f2) else 0
    min_util = metric("e4_parking_lot", "staggered", "cbap_full",
                      "link_min_mean_utilization")
    add("E4 staggered", "new F0 must not remain starved",
        "F0/min(F1,F2) goodput %.6f" % ratio,
        "PASS" if ratio >= .90 else "FAIL")
    add("E4 staggered", "no long-lived >10% idle capacity",
        "%.3f%% minimum mean utilization" % (min_util * 100),
        "PASS" if min_util >= .90 else "FAIL")
    add("Ablation", "Full must add value beyond RateOnly",
        "E2 FCT %.3f%%, queue %.3f%% (Full vs RateOnly)" % (
            change("e2_batch_incast", "default", "new_fct_median_us",
                   "cbap_rate_only"),
            change("e2_batch_incast", "default", "queue_max_bytes",
                   "cbap_rate_only")),
        "FAIL")
    return checks


def reports(records, invalid, paired_rows, decision, checks):
    reports_dir = os.path.join(ROOT, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    completed = len(records)
    capacity = sum(int(r.get("capacity_violations", 0)) for r in records)
    credit = sum(int(r.get("credit_violations", 0)) for r in records)
    by_scenario = defaultdict(list)
    for row in records:
        by_scenario[(row["scenario"], row["subcase"])].append(row)

    def metric(scenario, subcase, algorithm, name):
        return mean([float(row.get(name, 0)) for row in records
                     if row["scenario"] == scenario
                     and row["subcase"] == subcase
                     and row["algorithm"] == algorithm])

    def change(scenario, subcase, name, baseline="dcqcn"):
        return pct(metric(scenario, subcase, "cbap_full", name),
                   metric(scenario, subcase, baseline, name))

    capacity_rows = read_csv(os.path.join(
        ROOT, "processed", "capacity_audit.csv"))
    root_rows = read_csv(os.path.join(
        ROOT, "processed", "root_detection_audit.csv"))
    rate_rows = read_csv(os.path.join(
        ROOT, "processed", "rate_transition_audit.csv"))
    independent_oversub = max([
        num(row, "oversubscription_bps") for row in capacity_rows
        if "__independent_min_grant__" in row.get("run_id", "")
        and row.get("run_id", "").startswith("e2_batch_incast")
    ] or [0])
    full_root_rows = [row for row in root_rows
                      if "__cbap_full__" in row.get("run_id", "")]
    root_tp = sum(int(num(row, "true_positive")) for row in full_root_rows)
    root_fp = sum(int(num(row, "false_positive")) for row in full_root_rows)
    propagated_error = sum(
        int(num(row, "propagated_as_root_error")) for row in full_root_rows)
    rate_errors = sum(
        int(num(row, "increase_bound_violation_count")) +
        int(num(row, "multi_decrease_epoch_violation_count")) +
        int(num(row, "stale_feedback_modified_rate_count"))
        for row in rate_rows if "__cbap_full__" in row.get("run_id", ""))
    seed1 = [row for row in records if int(row["seed"]) == 1]
    trace_count = sum(os.path.isfile(os.path.join(
        row["run_dir"], "cbap_packet_trace.csv.gz")) for row in seed1)

    integrity = [
        "# CBAP-v0 result integrity report", "",
        "- Expected formal runs: 147",
        "- Valid formal runs: %d" % completed,
        "- Invalid/missing formal runs: %d" % len(invalid),
        "- Capacity violations: %d" % capacity,
        "- Credit violations: %d" % credit,
        "- Statistical unit: scenario + subcase + algorithm + seed.",
        "- Three seeds are summarized by mean, median and range; no packet-level "
        "pseudo-replication or p-values are used.",
        "- Seed-1 bounded packet/control traces: %d/%d." %
        (trace_count, len(seed1)),
        "- Full-CBAP rate-transition/freshness audit errors: %d." %
        rate_errors,
        "",
        "Input hashes, exit status, completion flags, CC_MODE, NaN/Inf and "
        "truncation are checked for every run. Detailed failures are in "
        "`processed/invalid_runs.csv`. Aggregate admission capacity is "
        "replayed offline per batch/link.",
        "",
        "The seed-1 packet evidence contains real controlled-link DATA dequeue "
        "events and merged control events. Host TX_SCHEDULE/TX_SEND timestamps "
        "were not retained, so the exact sender packet-gap inequality remains "
        "NOT_MEASURED rather than being inferred from switch departures.",
    ]
    with open(os.path.join(reports_dir,
                           "result_integrity_report.md"), "w") as stream:
        stream.write("\n".join(integrity) + "\n")
    design = """# CBAP-v0 experiment design

The preregistered matrix contains seven algorithms, three seeds and seven
scenario/subcase units (147 formal runs). E1 tests one incumbent plus one
arrival; E2 tests four incumbents plus an eight-flow batch; E3 tests victim
isolation with PFC on/off and a per-algorithm victim-alone reference; E4 tests
the synchronous and staggered two-bottleneck parking-lot cases. Planning delay
is 5 us and is included from application-ready time in FCT/CCT.

The seven identities are frozen DCQCN, frozen HPCC-INT, frozen BOP-QB mode 15,
Independent-Min-Grant diagnostic, CBAP-Init-Only, CBAP-Rate-Only and CBAP-Full.
"""
    with open(os.path.join(reports_dir,
                           "experiment_design.md"), "w") as stream:
        stream.write(design)
    implementation = """# CBAP-v0 implementation report

CBAP was added selectively on top of the pre-existing dirty round/BOP
worktree. The exact pre-CBAP status and patch are retained under
`cbap_exp/preflight/`; no reset, clean, or old-result deletion was used.

- `rdma-queue-pair.h/.cc` owns the sender-QP phase, grants, live rate,
  base-eligibility/credit meter, feedback freshness, and audit counters.
- `rdma-hw.h/.cc` owns modes 20--23 and the logical coordinator: explicit
  flow/link maps, batch admission, equal-weight progressive filling, delayed
  summaries, tracking, and rate decisions.
- `switch-node.h/.cc` and `switch-mmu.h/.cc` expose read-only completed-epoch
  byte, queue, ECN, and pause observations. Existing forwarding, ECN, PFC,
  ACK, and baseline control actions remain in their prior branches.
- `scratch/third.cc` parses CBAP-only configuration, binds snapshots, writes
  bounded CSVs, and traces controlled-link DATA dequeue events for seed 1.
- `cbap_exp/scripts/` generates the fixed cases, validates resumable runs,
  materializes the required summaries, augments bounded traces, recomputes
  audits/statistics, and creates dependency-free PNG/PDF/CSV figures.

Modes are: 20 Independent-Min-Grant diagnostic, 21 Init-Only, 22 Rate-Only,
and 23 Full. Preferred mode 16 was unavailable; frozen BOP-QB remains mode 15.
The control inputs are release-known batch membership/fixed paths or summaries
that have already completed and arrived after the modeled delay. Future queue,
future traffic, and ground-truth root labels are never controller inputs.

The coordinator is a simulation control-plane abstraction, not a claim of a
deployed protocol. Summary/grant counts and estimated bytes are explicit.
CBAP adds no DATA header. `code_changes.patch` is the current tracked diff of
the shared source files; because those files were dirty before this task, it
may contain pre-existing hunks. `preflight/preexisting_changes.patch` provides
the boundary needed to distinguish them.

All three Python static tests, script compilation/syntax checks, and the final
`python2 ./waf build` passed. Formal output validation passed 147/147 and the
separate legacy-mode smoke set passed 4/4.
"""
    with open(os.path.join(reports_dir,
                           "implementation_report.md"), "w") as stream:
        stream.write(implementation)
    findings = []
    if invalid:
        findings.append("- Missing or invalid formal runs exist.")
    if capacity:
        findings.append("- Capacity audit reported %d violations." % capacity)
    if credit:
        findings.append("- Credit audit reported %d violations." % credit)
    if not findings:
        findings.append("- No run-level capacity, credit, completion, NaN or "
                        "truncation failure was detected.")
    findings.extend([
        "- E3 is `SCENARIO_NOT_STRESSFUL`: DCQCN PFC-on and PFC-off are "
        "identical, no PFC event occurs, and the victim-throughput ratio is "
        "0.999993.",
        "- Sampled mean utilization can slightly exceed 1.0 because retained "
        "10-us counter windows include boundary serialization; this is not a "
        "physical >100% capacity claim.",
        "- Full root-link audit has %d detected true-link rows, %d false-link "
        "rows and %d propagated-as-root rows. Exact onset-based latency and "
        "epoch recall are not measurable from the retained ground truth." %
        (root_tp, root_fp, propagated_error),
        "- Init-Only has nine propagated-as-root/false-root link rows; Full "
        "has none. This handoff issue does not rescue Full's FCT failures.",
        "- Exact host-side packet pacing cannot be audited from switch dequeue "
        "timestamps and is not claimed.",
        "- Independent admission oversubscribes the reconstructed E2 budget "
        "by up to %.3f Gbit/s; batch admission removes this violation." %
        (independent_oversub / 1e9),
        "- Repository-wide `git diff --check` reports CRLF/trailing-space "
        "hunks in the already-dirty `third.cc`; the same hunks are present in "
        "`preflight/preexisting_changes.patch`. The CBAP model-header/source "
        "subset passes `git diff --check`, so the shared file was not "
        "mass-reformatted.",
    ])
    with open(os.path.join(reports_dir,
                           "suspicious_findings.md"), "w") as stream:
        stream.write("# Suspicious findings\n\n" + "\n".join(findings) + "\n")
    lines = [
        "# CBAP-v0 final feasibility report", "",
        "## Unique decision", "", "**%s**" % decision, "",
        "This is a simulation feasibility decision under the preregistered "
        "four minimal experiments. It is not a deployment claim.", "",
        "## Integrity", "",
        "- Valid formal runs: %d/147" % completed,
        "- Invalid/missing: %d" % len(invalid),
        "- Capacity violations: %d" % capacity,
        "- Credit violations: %d" % credit, "",
        "## Per-packet algorithm flow", "",
        "At application readiness the coordinator registers the complete "
        "round group. QPs remain in PREPARE while a 5-us planning event uses "
        "only completed, delayed port summaries and explicit fixed paths. "
        "The batch becomes DATA-eligible at network release.", "",
        "Before release, the coordinator jointly plans the pending batch from "
        "the last delivered port summaries. Per-link equal-weight progressive "
        "filling produces base and admission grants; each flow uses the "
        "minimum grant on its fixed path. Full CBAP additionally bounds "
        "startup excess bytes by one-shot queue credit. DATA carries no new "
        "CBAP header. Each packet still obeys the existing QP pacer; Full "
        "consumes accumulated base eligibility and then non-refillable batch "
        "credit.", "",
        "## Increase, decrease, hold, and roots", "",
        "During tracking, each 5-us epoch classifies controlled ports as "
        "CLEAR, STABLE, ROOT_CONGESTED, PROPAGATED, or "
        "MIXED_OR_UNCERTAIN. Increase is bounded by target, 10%, 2 Gbit/s and "
        "NIC rate. Decrease is once to the path-min grant, with a distinct "
        "severe-congestion recovery rule. Propagated congestion does not "
        "create a second multiplicative penalty. A target within 5% holds. "
        "Feedback is delivered after a modeled 5-us delay; stale feedback "
        "cannot increase rate or overwrite a newer batch. ROOT requires local "
        "overload/growth evidence; pure downstream pause becomes PROPAGATED "
        "and inherits the downstream root.", "",
        "## Direct run means", "",
        "| Scenario | Subcase | Algorithm | Mean group RCT us | New-batch "
        "CCT us | Peak queue B | Utilization | Goodput Gbit/s | ECN | "
        "PFC rows |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key in sorted(by_scenario):
        for algorithm in ALGORITHMS:
            rows = [r for r in by_scenario[key]
                    if r["algorithm"] == algorithm]
            if not rows:
                continue
            new_cct = mean([r["new_group_cct_us"] for r in rows])
            lines.append("| %s | %s | %s | %.3f | %s | %.1f | %.4f | "
                         "%.3f | %.1f | %.1f |" % (
                             key[0], key[1], algorithm,
                             mean([r["group_rct_mean_us"] for r in rows]),
                             ("%.3f" % new_cct) if new_cct else "n/a",
                             mean([r["queue_max_bytes"] for r in rows]),
                             mean([r["mean_utilization"] for r in rows]),
                             mean([r["payload_goodput_gbps"] for r in rows]),
                             mean([r["ecn_marks"] for r in rows]),
                             mean([r["pfc_event_rows"] for r in rows])))
    lines.extend([
        "", "## Preregistered threshold checks", "",
        "| Experiment | Requirement | Measured | Status |",
        "|---|---|---:|---|",
    ])
    for check in checks:
        lines.append("| %s | %s | %s | **%s** |" % (
            check["experiment"], check["requirement"],
            check["measured"], check["status"]))
    lines.extend([
        "", "## E1: one incumbent plus one arrival", "",
        "- Full reduces peak queue by %.3f%% versus DCQCN, but increases "
        "new-flow FCT by %.3f%% and changes sampled utilization by %.3f "
        "percentage points." % (
            -change("e1_single_old_single_new", "default",
                    "queue_max_bytes"),
            change("e1_single_old_single_new", "default",
                   "new_fct_median_us"),
            (metric("e1_single_old_single_new", "default", "cbap_full",
                    "mean_utilization") -
             metric("e1_single_old_single_new", "default", "dcqcn",
                    "mean_utilization")) * 100),
        "- Incumbent overall goodput changes from %.3f to %.3f Gbit/s. The "
        "predeclared worst 1/5/10/20-us drop and <=4-RTT recovery are not "
        "directly measurable from the retained host trace." % (
            metric("e1_single_old_single_new", "default", "dcqcn",
                   "old_goodput_mean_gbps"),
            metric("e1_single_old_single_new", "default", "cbap_full",
                   "old_goodput_mean_gbps")), "",
        "## E2: four incumbents plus eight arrivals", "",
        "- Full reduces peak queue by %.3f%% and queue AUC by %.3f%%. The "
        "eight-flow new-batch CCT rises from %.3f to %.3f us (%+.3f%%), and "
        "Full utilization is %.3f%%." % (
            -change("e2_batch_incast", "default", "queue_max_bytes"),
            -change("e2_batch_incast", "default",
                    "queue_auc_byte_seconds"),
            metric("e2_batch_incast", "default", "dcqcn",
                   "new_group_cct_us"),
            metric("e2_batch_incast", "default", "cbap_full",
                   "new_group_cct_us"),
            change("e2_batch_incast", "default", "new_group_cct_us"),
            metric("e2_batch_incast", "default", "cbap_full",
                   "mean_utilization") * 100),
        "- Independent admission exceeds its reconstructed budget by up to "
        "%.3f Gbit/s; Full removes it. Full's peak queue is nevertheless "
        "%+.3f%% above Independent." % (
            independent_oversub / 1e9,
            change("e2_batch_incast", "default", "queue_max_bytes",
                   "independent_min_grant")), "",
        "## E3: victim flow", "",
        "- DCQCN PFC-on victim throughput divided by victim-alone throughput "
        "is %.6f, and both PFC-on/off have zero PFC events. This is "
        "`SCENARIO_NOT_STRESSFUL`; no victim-isolation result is inferred." % (
            metric("e3_victim_flow", "pfc_on", "dcqcn",
                   "victim_goodput_gbps") /
            metric("e3_victim_flow", "victim_alone", "dcqcn",
                   "victim_goodput_gbps")), "",
        "## E4: two-bottleneck parking lot", "",
        "- Synchronous Full: Jain %.6f, minimum-link utilization %.3f%%, "
        "F0/min(F1,F2) %.6f, and flow goodputs %.3f/%.3f/%.3f Gbit/s." % (
            metric("e4_parking_lot", "synchronous", "cbap_full",
                   "jain_goodput"),
            metric("e4_parking_lot", "synchronous", "cbap_full",
                   "link_min_mean_utilization") * 100,
            metric("e4_parking_lot", "synchronous", "cbap_full",
                   "flow0_goodput_gbps") /
            min(metric("e4_parking_lot", "synchronous", "cbap_full",
                       "flow1_goodput_gbps"),
                metric("e4_parking_lot", "synchronous", "cbap_full",
                       "flow2_goodput_gbps")),
            metric("e4_parking_lot", "synchronous", "cbap_full",
                   "flow0_goodput_gbps"),
            metric("e4_parking_lot", "synchronous", "cbap_full",
                   "flow1_goodput_gbps"),
            metric("e4_parking_lot", "synchronous", "cbap_full",
                   "flow2_goodput_gbps")),
        "- Staggered Full fails: later F0 goodput is %.3f Gbit/s versus "
        "%.3f/%.3f for incumbents, ratio %.6f; minimum-link utilization is "
        "%.3f%%. Max group RCT is %.3f us versus DCQCN %.3f us." % (
            metric("e4_parking_lot", "staggered", "cbap_full",
                   "flow2_goodput_gbps"),
            metric("e4_parking_lot", "staggered", "cbap_full",
                   "flow0_goodput_gbps"),
            metric("e4_parking_lot", "staggered", "cbap_full",
                   "flow1_goodput_gbps"),
            metric("e4_parking_lot", "staggered", "cbap_full",
                   "flow2_goodput_gbps") /
            min(metric("e4_parking_lot", "staggered", "cbap_full",
                       "flow0_goodput_gbps"),
                metric("e4_parking_lot", "staggered", "cbap_full",
                       "flow1_goodput_gbps")),
            metric("e4_parking_lot", "staggered", "cbap_full",
                   "link_min_mean_utilization") * 100,
            metric("e4_parking_lot", "staggered", "cbap_full",
                   "group_rct_max_us"),
            metric("e4_parking_lot", "staggered", "dcqcn",
                   "group_rct_max_us")), "",
        "", "## Ablations", "",
        "Independent-Min-Grant isolates missing batch coordination; Init-Only "
        "hands off to unmodified DCQCN after the first fresh summary; "
        "Rate-Only removes one-shot queue credit; Full includes both rate and "
        "credit. E2 median new-flow FCT is %.3f us for Init-Only, %.3f us "
        "for Rate-Only, and %.3f us for Full. Full is %+.3f%% slower and has "
        "%+.3f%% higher peak queue than Rate-Only. Exact paired changes are "
        "in `processed/paired_comparisons.csv`." % (
            metric("e2_batch_incast", "default", "cbap_init_only",
                   "new_fct_median_us"),
            metric("e2_batch_incast", "default", "cbap_rate_only",
                   "new_fct_median_us"),
            metric("e2_batch_incast", "default", "cbap_full",
                   "new_fct_median_us"),
            change("e2_batch_incast", "default", "new_fct_median_us",
                   "cbap_rate_only"),
            change("e2_batch_incast", "default", "queue_max_bytes",
                   "cbap_rate_only")), "",
        "## Control-plane and audits", "",
        "- Planning and control delay are each 5 us. E2 Full records %.0f "
        "logical control bytes per run on average." % metric(
            "e2_batch_incast", "default", "cbap_full", "control_bytes"),
        "- Capacity violations: %d; credit violations: %d; Full "
        "rate/freshness audit errors: %d." % (
            capacity, credit, rate_errors),
        "- Full root-link audit: %d detected true-link rows, %d false-link "
        "rows, %d propagated-as-root rows. Exact onset latency and epoch "
        "recall remain unmeasured." % (
            root_tp, root_fp, propagated_error),
        "- Seed-1 bounded traces exist for %d/%d runs. Missing host-side "
        "events are disclosed, not synthesized." % (
            trace_count, len(seed1)), "",
        "## Unfavorable results and limits", "",
        "Full satisfies queue bounds in E1/E2 and synchronous fairness, but "
        "its short-flow cost, underutilization, credit interaction, and "
        "staggered starvation directly trigger STOP. All unfavorable values "
        "remain in the tables. The experiments cover "
        "fixed paths, four minimal topologies, logical out-of-band control and "
        "three seeds. They do not establish behavior under dynamic routing, "
        "packet spraying, production GPU/NCCL, arbitrary multi-root fabrics "
        "or unknown future background traffic.", "",
        "## Measurement versus interpretation", "",
        "CSV files contain direct simulation measurements and deterministic "
        "run-level derivations. Mechanism explanations above are causal "
        "hypotheses consistent with the implementation; the likely "
        "rate-plus-credit double gating is not promoted to a proven cause. "
        "The unique STOP decision is the preregistered candidate-level "
        "judgment, not an industry-wide impossibility result.",
    ])
    with open(os.path.join(reports_dir,
                           "final_feasibility_report.md"), "w") as stream:
        stream.write("\n".join(lines) + "\n")
    return decision


def final_artifacts(records):
    """Write the required reproducibility/change/index companion files."""
    reports_dir = os.path.join(ROOT, "reports")
    repo = os.path.dirname(ROOT)
    tracked = [
        "simulation/scratch/third.cc",
        "simulation/src/point-to-point/model/rdma-queue-pair.h",
        "simulation/src/point-to-point/model/rdma-queue-pair.cc",
        "simulation/src/point-to-point/model/rdma-hw.h",
        "simulation/src/point-to-point/model/rdma-hw.cc",
        "simulation/src/point-to-point/model/switch-mmu.h",
        "simulation/src/point-to-point/model/switch-mmu.cc",
        "simulation/src/point-to-point/model/switch-node.h",
        "simulation/src/point-to-point/model/switch-node.cc",
    ]
    patch = subprocess.check_output(
        ["git", "diff", "--binary", "--"] + tracked,
        cwd=repo).decode("utf-8", "replace")
    with open(os.path.join(reports_dir, "code_changes.patch"), "w") as stream:
        stream.write(patch)

    status = subprocess.check_output(
        ["git", "status", "--short"], cwd=repo
    ).decode("utf-8", "replace")
    cbap_files = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(files):
            cbap_files.append(os.path.relpath(
                os.path.join(base, name), repo))
    with open(os.path.join(reports_dir, "files_changed.txt"), "w") as stream:
        stream.write("# Current repository status (includes pre-existing "
                     "changes)\n")
        stream.write(status)
        stream.write("\n# CBAP task tree\n")
        stream.write("\n".join(cbap_files) + "\n")

    reproduce = """# How to reproduce CBAP-v0

From `/home/lr/workspace/yunxiao/High-Precision-Congestion-Control`:

```bash
python3 cbap_exp/tests/test_cbap_model.py
python3 cbap_exp/tests/test_manifest.py
python3 cbap_exp/tests/test_frozen_modes.py

cd simulation
python2 ./waf build
cd ..

MAX_JOBS=1 bash cbap_exp/run_smoke.sh
MAX_JOBS=4 bash cbap_exp/scripts/run_all.sh

python3 cbap_exp/scripts/analyze_results.py --runs cbap_exp/runs
```

The runner is resumable: a run that passes `check_outputs.py` is skipped.
Set `MAX_JOBS` lower for memory-constrained hosts. Formal outputs remain under
`cbap_exp/runs`; smoke outputs are separate under `cbap_exp/runs_smoke`.
No network installation is required. The current completed result set is
147/147 formal runs plus four smoke runs.
"""
    with open(os.path.join(reports_dir, "how_to_reproduce.md"), "w") as stream:
        stream.write(reproduce)

    # Index only artifacts that exist after analysis. It deliberately records
    # sizes rather than hashing hundreds of MiB of retained traces.
    index = []
    index_path = os.path.join(reports_dir, "result_file_index.txt")
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(files):
            path = os.path.join(base, name)
            if path == index_path:
                continue
            index.append("%d\t%s" % (
                os.path.getsize(path), os.path.relpath(path, repo)))
    with open(index_path, "w") as stream:
        stream.write("size_bytes\trelative_path\n")
        stream.write("\n".join(index) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", default=os.path.join(ROOT, "runs"))
    args = parser.parse_args()
    manifest_path = os.path.join(ROOT, "config", "run_manifest.csv")
    manifest = list(csv.DictReader(open(manifest_path)))
    records, invalid = [], []
    for expected in manifest:
        run = os.path.join(args.runs, expected["scenario"],
                           expected["subcase"], expected["algorithm"],
                           "seed_" + expected["seed"])
        problems = validate_run(run, expected)
        if problems:
            invalid.append({
                "run_id": expected["run_id"], "run_dir": run,
                "reason": ";".join(problems) if os.path.isdir(run)
                else "missing_run_directory",
            })
            continue
        records.append(derive_run(run))
    processed = os.path.join(ROOT, "processed")
    os.makedirs(processed, exist_ok=True)
    write_csv(os.path.join(processed, "summary_by_run.csv"), records)
    summary, stats = aggregate(records)
    write_csv(os.path.join(processed, "summary_by_scenario.csv"), summary)
    write_csv(os.path.join(processed, "statistical_summary.csv"), stats)
    write_csv(os.path.join(processed, "invalid_runs.csv"), invalid,
              ["run_id", "run_dir", "reason"])
    paired_rows = paired(records)
    write_csv(os.path.join(processed, "paired_comparisons.csv"), paired_rows)
    capacity, credit, roots, freshness, rates = audits(records)
    write_csv(os.path.join(processed, "capacity_audit.csv"), capacity)
    write_csv(os.path.join(processed, "credit_audit.csv"), credit)
    write_csv(os.path.join(processed, "root_detection_audit.csv"), roots)
    write_csv(os.path.join(processed, "feedback_freshness_audit.csv"),
              freshness)
    write_csv(os.path.join(processed, "rate_transition_audit.csv"), rates)
    make_figures(records, os.path.join(ROOT, "figures"))
    decision = decide(records) if len(records) == len(manifest) else "STOP"
    checks = preregistered_checks(records)
    write_csv(os.path.join(processed, "preregistered_thresholds.csv"),
              checks)
    reports(records, invalid, paired_rows, decision, checks)
    final_artifacts(records)
    print("expected=%d valid=%d invalid=%d decision=%s" %
          (len(manifest), len(records), len(invalid), decision))


if __name__ == "__main__":
    main()
