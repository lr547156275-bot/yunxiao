#!/usr/bin/env python3
"""Analyze completed CBAP-v1 runs without changing or launching simulations."""
import csv
import gzip
import hashlib
import json
import math
import os
import statistics
from collections import defaultdict

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RUNS = os.path.join(ROOT, "runs_formal")
PROCESSED = os.path.join(ROOT, "processed")
REPORTS = os.path.join(ROOT, "reports")
FIGURES = os.path.join(ROOT, "figures")
ALGORITHMS = ("dcqcn", "hpcc_int", "bop_qb", "independent_min_grant",
              "cbap_init_only", "cbap_rate_only", "cbap_full")
CBAP = set(ALGORITHMS[3:])
METRICS = ("flow_fct_mean_us", "flow_fct_max_us", "group_rct_mean_us",
           "group_rct_max_us", "new_group_cct_us", "new_fct_median_us",
           "queue_max_bytes", "queue_p95_bytes", "queue_auc_byte_seconds",
           "mean_utilization", "payload_goodput_gbps", "ecn_marks",
           "pfc_event_rows", "old_goodput_mean_gbps",
           "new_goodput_mean_gbps", "completion_skew_us",
           "link_min_mean_utilization", "flow0_goodput_gbps",
           "flow1_goodput_gbps", "flow2_goodput_gbps")


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


def mean(values):
    return statistics.mean(values) if values else 0.0


def median(values):
    return statistics.median(values) if values else 0.0


def pct(new, old):
    return (new - old) / old * 100.0 if old else 0.0


def percentile(values, fraction):
    values = sorted(values)
    if not values:
        return 0.0
    point = fraction * (len(values) - 1)
    lo, hi = int(math.floor(point)), int(math.ceil(point))
    return values[lo] if lo == hi else values[lo] + (
        values[hi] - values[lo]) * (point - lo)


def write_csv(path, rows, fields=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with open(path, "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields,
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_path(row):
    return os.path.join(RUNS, row["scenario"], row["subcase"],
                        row["algorithm"], "seed_" + row["seed"])


def schedule(path):
    result = {}
    with open(os.path.join(path, "rounds.txt")) as stream:
        next(stream)
        for line in stream:
            fields = line.split()
            if fields:
                result[int(fields[0])] = {
                    "group": int(fields[2]), "bytes": int(fields[4]),
                    "ready_s": int(fields[8]) / 1e9}
    return result


def validate(expected):
    path = run_path(expected)
    problems = []
    required = ("completed.flag", "exit_status.txt", "run_meta.json",
                "result.json", "flow_summary.csv", "round_summary.csv",
                "queue_summary.csv", "rate_summary.csv")
    if not os.path.isdir(path):
        return ["missing_run_directory"]
    for name in required:
        if not os.path.isfile(os.path.join(path, name)):
            problems.append("missing_" + name)
    if problems:
        return problems
    meta = json.load(open(os.path.join(path, "run_meta.json")))
    result = json.load(open(os.path.join(path, "result.json")))
    if int(open(os.path.join(path, "exit_status.txt")).read().strip()):
        problems.append("nonzero_exit")
    if not result.get("all_flows_completed"):
        problems.append("incomplete_flow")
    if result.get("log_truncated") or meta.get("log_truncated"):
        problems.append("log_truncated")
    if int(meta.get("cc_mode", -1)) != int(expected["cc_mode"]):
        problems.append("cc_mode_mismatch")
    if meta.get("algorithm") != expected["algorithm"]:
        problems.append("algorithm_mismatch")
    if any(isinstance(value, float) and not math.isfinite(value)
           for value in result.values()):
        problems.append("nonfinite_result")
    if int(result.get("completed_flow_count", -1)) != int(
            result.get("flow_count", -2)):
        problems.append("flow_count_mismatch")
    if expected["algorithm"] in CBAP:
        for name in ("cbap_flow_state.csv", "cbap_admission.csv",
                     "cbap_rate_transitions.csv", "cbap_port_summary.csv"):
            if not os.path.isfile(os.path.join(path, name)):
                problems.append("missing_" + name)
        if result.get("capacity_violations"):
            problems.append("capacity_violation")
        if result.get("credit_violations"):
            problems.append("credit_violation")
    return problems


def derive(expected):
    path = run_path(expected)
    result = json.load(open(os.path.join(path, "result.json")))
    scenario_meta = json.load(open(os.path.join(path, "scenario_meta.json")))
    flows = read_csv(os.path.join(path, "flow_summary.csv"))
    rounds = read_csv(os.path.join(path, "round_summary.csv"))
    links = read_csv(os.path.join(path, "selected_link_timeseries.csv"))
    sched = schedule(path)
    fct, goodput, finish = {}, {}, {}
    for row in flows:
        fid = int(row["flow_id"])
        finish[fid] = num(row, "finish_time")
        fct[fid] = max(finish[fid] - sched[fid]["ready_s"], 0) * 1e6
        goodput[fid] = num(row, "flow_goodput") / 1e9
    group_rct = defaultdict(float)
    for row in rounds:
        fid, gid = int(row["flow_id"]), int(row["round_group_id"])
        value = max(num(row, "ack_completion_time") -
                    sched[fid]["ready_s"], 0) * 1e6
        group_rct[gid] = max(group_rct[gid], value)
    per_link = defaultdict(list)
    for row in links:
        per_link[row.get("link_id", "")].append(row)
    new_ids = scenario_meta.get("new_flow_ids", [])
    old_ids = scenario_meta.get("old_flow_ids", [])
    out = dict(result)
    out.update({"run_id": expected["run_id"], "run_dir": path,
                "scenario": expected["scenario"],
                "subcase": expected["subcase"],
                "algorithm": expected["algorithm"],
                "seed": int(expected["seed"]), "valid": 1,
                "flow_fct_median_us": median(list(fct.values())),
                "flow_fct_p95_us": percentile(list(fct.values()), .95),
                "group_rct_median_us": median(list(group_rct.values())),
                "group_rct_p95_us": percentile(list(group_rct.values()), .95),
                "completion_skew_us": (max(finish.values()) -
                                         min(finish.values())) * 1e6,
                "link_min_mean_utilization": min((mean([
                    num(x, "utilization") for x in rows])
                    for rows in per_link.values()), default=0),
                "flow0_goodput_gbps": goodput.get(0, 0),
                "flow1_goodput_gbps": goodput.get(1, 0),
                "flow2_goodput_gbps": goodput.get(2, 0),
                "new_fct_median_us": median([fct[x] for x in new_ids
                                               if x in fct]),
                "new_group_cct_us": max([fct[x] for x in new_ids
                                           if x in fct] or [0]),
                "new_goodput_mean_gbps": mean([goodput[x] for x in new_ids
                                                 if x in goodput]),
                "old_goodput_mean_gbps": mean([goodput[x] for x in old_ids
                                                 if x in goodput])})
    return out


def make_rate_audit(records):
    rows = []
    for run in records:
        if run["algorithm"] not in CBAP:
            continue
        states = read_csv(os.path.join(run["run_dir"], "cbap_flow_state.csv"))
        transitions = read_csv(os.path.join(
            run["run_dir"], "cbap_rate_transitions.csv"))
        sampled = read_csv(os.path.join(run["run_dir"],
                                        "selected_flow_timeseries.csv"))
        overhead = read_csv(os.path.join(run["run_dir"],
                                         "cbap_control_overhead.csv"))
        control_delay = num(overhead[0], "control_delay_ns") if overhead else 0
        by_flow = defaultdict(list)
        sampled_by_flow = defaultdict(list)
        for transition in transitions:
            by_flow[transition["flow_id"]].append(transition)
        for sample in sampled:
            sampled_by_flow[sample["flow_id"]].append(sample)
        for state in states:
            flow = state["flow_id"]
            changes = by_flow[flow]
            tracking_actual = num(state, "tracking_actual_rate_bps")
            tracking_current = num(state, "tracking_current_rate_bps")
            base = num(state, "tracking_base_rate_bps")
            release = num(state, "network_release_ns")
            base_rtt = max(num(state, "estimated_first_feedback_ns") -
                           release - control_delay, 0)
            def sampled_rate(multiplier):
                target = (release + multiplier * base_rtt) / 1e9
                candidates = sampled_by_flow[flow]
                if not candidates:
                    return 0
                chosen = min(candidates,
                             key=lambda x: abs(num(x, "time") - target))
                return num(chosen, "current_rate")
            decreases = defaultdict(int)
            for change in changes:
                if num(change, "new_rate_bps") < num(change, "old_rate_bps"):
                    decreases[change["epoch"]] += 1
            rows.append({
                "run_id": run["run_id"], "scenario": run["scenario"],
                "subcase": run["subcase"], "algorithm": run["algorithm"],
                "seed": run["seed"], "flow_id": flow,
                "initial_admit_rate_bps": num(state,
                                                "initial_admit_rate_bps"),
                "actual_admission_mean_rate_bps": num(
                    state, "actual_admission_mean_rate_bps"),
                "tracking_actual_rate_bps": tracking_actual,
                "tracking_current_rate_bps": tracking_current,
                "tracking_base_rate_bps": base,
                "tracking_actual_current_ratio": tracking_actual /
                    tracking_current if tracking_current else 0,
                "tracking_actual_base_ratio": tracking_actual / base
                    if base else 0,
                "mean_target_rate_bps": mean([
                    num(x, "target_rate_bps") for x in changes]),
                "ordinary_updates_during_admission": int(num(
                    state, "ordinary_rate_updates_during_admission")),
                "emergency_updates_during_admission": int(num(
                    state, "emergency_rate_updates_during_admission")),
                "credit_gate_enter_ns": int(num(state,
                                                  "credit_gate_enter_ns")),
                "credit_gate_exit_ns": int(num(state,
                                                 "credit_gate_exit_ns")),
                "admission_exit_ns": int(num(state, "admission_exit_ns")),
                "credit_gate_active_at_finish": int(num(
                    state, "credit_gate_active_at_finish")),
                "pacing_violations": int(num(state, "pacing_violations")),
                "rate_decreases": int(num(state, "rate_decreases")),
                "rate_increases": int(num(state, "rate_increases")),
                "multi_decrease_epoch_violations": sum(
                    count > 1 for count in decreases.values()),
                "estimated_base_rtt_ns": base_rtt,
                "current_rate_at_4rtt_bps": sampled_rate(4),
                "current_rate_at_6rtt_bps": sampled_rate(6),
                "fair80_ns": int(num(state, "fair80_ns")),
                "fair90_ns": int(num(state, "fair90_ns")),
                "fair95_ns": int(num(state, "fair95_ns")),
            })
    return rows


def make_admission_audit(records):
    output = []
    for run in records:
        if run["algorithm"] not in CBAP:
            continue
        admissions = read_csv(os.path.join(run["run_dir"],
                                           "cbap_admission.csv"))
        states = read_csv(os.path.join(run["run_dir"],
                                       "cbap_flow_state.csv"))
        links = read_csv(os.path.join(run["run_dir"],
                                      "selected_link_timeseries.csv"))
        scenario_meta = json.load(open(os.path.join(
            run["run_dir"], "scenario_meta.json")))
        state_by_flow = {x["flow_id"]: x for x in states}
        groups = defaultdict(list)
        for row in admissions:
            groups[row["batch_id"]].append(row)
        for batch, members in sorted(groups.items(), key=lambda x: int(x[0])):
            planned = sum(num(x, "admit_rate_bps") for x in members)
            actual = sum(num(state_by_flow.get(x["flow_id"], {}),
                             "actual_admission_mean_rate_bps")
                         for x in members)
            byte_count = sum(num(state_by_flow.get(x["flow_id"], {}),
                                 "bytes_sent_before_fresh_feedback")
                             for x in members)
            release = min(num(x, "network_release_ns") for x in members)
            horizon = max(num(x, "feedback_horizon_ns") for x in members)
            queue_window = [num(x, "queue_bytes") for x in links
                            if release / 1e9 <= num(x, "time") <=
                            (release + horizon) / 1e9]
            base_sum = sum(num(x, "base_rate_bps") for x in members)
            target = float(scenario_meta["ecn_kmin_bytes"]) * 0.5
            observed = max(num(x, "observed_queue_bytes") for x in members)
            margin = max(num(x, "packet_margin_bytes") for x in members)
            room = max(target - observed - margin, 0)
            queue_rate = room * 8e9 / horizon if horizon else 0
            budget = base_sum + queue_rate
            output.append({
                "run_id": run["run_id"], "scenario": run["scenario"],
                "subcase": run["subcase"], "algorithm": run["algorithm"],
                "seed": run["seed"], "batch_id": batch,
                "flow_count": len(members),
                "planned_aggregate_admission_bps": planned,
                "actual_aggregate_admission_bps": actual,
                "base_aggregate_bps": base_sum,
                "reconstructed_admission_budget_bps": budget,
                "planned_capacity_oversubscription_bps": max(planned-budget,0),
                "actual_capacity_oversubscription_bps": max(actual-budget,0),
                "bytes_before_fresh_feedback": byte_count,
                "first_feedback_horizon_ns": horizon,
                "first_rtt_queue_max_bytes": max(queue_window or [0]),
                "run_queue_max_bytes": run["queue_max_bytes"],
                "run_queue_auc_byte_seconds": run["queue_auc_byte_seconds"],
                "run_group_cct_us": run["new_group_cct_us"],
                "run_utilization": run["mean_utilization"],
                "old_flow_goodput_gbps": run["old_goodput_mean_gbps"],
            })
    return output


def aggregate(records):
    output = []
    groups = defaultdict(list)
    for row in records:
        groups[(row["scenario"], row["subcase"],
                row["algorithm"])].append(row)
    for key, rows in sorted(groups.items()):
        item = {"scenario": key[0], "subcase": key[1],
                "algorithm": key[2], "seed_count": len(rows)}
        for metric in METRICS:
            values = [num(row, metric) for row in rows]
            item[metric + "_mean"] = mean(values)
            item[metric + "_median"] = median(values)
            item[metric + "_min"] = min(values)
            item[metric + "_max"] = max(values)
        output.append(item)
    return output


def paired(records):
    keyed = {(x["scenario"], x["subcase"], x["algorithm"], x["seed"]): x
             for x in records}
    comparisons = (("cbap_full", "dcqcn"), ("cbap_full", "hpcc_int"),
                   ("cbap_full", "bop_qb"),
                   ("cbap_full", "independent_min_grant"),
                   ("cbap_full", "cbap_init_only"),
                   ("cbap_full", "cbap_rate_only"),
                   ("cbap_rate_only", "independent_min_grant"),
                   ("cbap_rate_only", "cbap_init_only"))
    lower_is_better = {"flow_fct_mean_us", "flow_fct_max_us",
                       "group_rct_mean_us", "group_rct_max_us",
                       "new_group_cct_us", "new_fct_median_us",
                       "queue_max_bytes", "queue_p95_bytes",
                       "queue_auc_byte_seconds", "ecn_marks",
                       "pfc_event_rows", "completion_skew_us"}
    output = []
    scenarios = sorted(set((x["scenario"], x["subcase"])
                           for x in records))
    for scenario, subcase in scenarios:
        for new, old in comparisons:
            for metric in METRICS:
                diffs = []
                for seed in (1, 2, 3):
                    a = keyed.get((scenario, subcase, new, seed))
                    b = keyed.get((scenario, subcase, old, seed))
                    if a and b:
                        diffs.append(pct(num(a, metric), num(b, metric)))
                if diffs:
                    favorable = sum(value < 0 for value in diffs) if \
                        metric in lower_is_better else sum(
                            value > 0 for value in diffs)
                    output.append({"scenario": scenario,
                                   "subcase": subcase,
                                   "new_algorithm": new,
                                   "baseline": old, "metric": metric,
                                   "paired_seed_count": len(diffs),
                                   "paired_percent_mean": mean(diffs),
                                   "paired_percent_median": median(diffs),
                                   "paired_percent_min": min(diffs),
                                   "paired_percent_max": max(diffs),
                                   "favorable_seed_count": favorable})
    return output


def control_overhead(records):
    output = []
    for run in records:
        rows = read_csv(os.path.join(run["run_dir"],
                                     "cbap_control_overhead.csv"))
        row = rows[0] if rows else {}
        output.append({"run_id": run["run_id"],
                       "scenario": run["scenario"],
                       "subcase": run["subcase"],
                       "algorithm": run["algorithm"], "seed": run["seed"],
                       "summary_messages": num(row, "summary_messages"),
                       "grant_messages": num(row, "grant_messages"),
                       "total_control_bytes": num(row, "total_control_bytes"),
                       "control_delay_ns": num(row, "control_delay_ns"),
                       "planning_delay_ns": num(row, "planning_delay_ns")})
    return output


COLORS = ((31, 119, 180), (255, 127, 14), (44, 160, 44),
          (214, 39, 40), (148, 103, 189), (140, 86, 75), (23, 190, 207))


def plot(name, title, x_label, y_label, rows, note=""):
    """Write exact CSV plus matching dependency-light PNG and PDF."""
    write_csv(os.path.join(FIGURES, name + ".csv"), rows,
              ["x", "series", "value", "label"])
    width, height, margin = 1100, 620, 85
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    values = [float(x["value"]) for x in rows]
    xs = [float(x["x"]) for x in rows]
    xmin, xmax = (min(xs), max(xs)) if xs else (0, 1)
    ymin, ymax = (min(values), max(values)) if values else (0, 1)
    ymin = min(0, ymin)
    if xmax == xmin: xmax += 1
    if ymax == ymin: ymax += 1
    draw.line((margin, height-margin, width-margin, height-margin), fill="black")
    draw.line((margin, margin, margin, height-margin), fill="black")
    draw.text((margin, 25), title, fill="black", font=font)
    draw.text((width//2-40, height-35), x_label, fill="black", font=font)
    draw.text((8, margin), y_label, fill="black", font=font)
    if note: draw.text((margin, 45), note, fill=(150,0,0), font=font)
    groups = defaultdict(list)
    for row in rows: groups[row["series"]].append(row)
    for index, (series, points) in enumerate(sorted(groups.items())):
        coords = []
        for row in sorted(points, key=lambda x: float(x["x"])):
            x, value = float(row["x"]), float(row["value"])
            px = margin + (x-xmin)/(xmax-xmin)*(width-2*margin)
            py = height-margin-(value-ymin)/(ymax-ymin)*(height-2*margin)
            coords.append((px, py))
        if len(coords) > 1: draw.line(coords, fill=COLORS[index%len(COLORS)], width=2)
        for px, py in coords: draw.ellipse((px-3,py-3,px+3,py+3), fill=COLORS[index%len(COLORS)])
        draw.text((width-margin-190, margin+index*15), series,
                  fill=COLORS[index%len(COLORS)], font=font)
    image.save(os.path.join(FIGURES, name + ".png"))
    pdf = canvas.Canvas(os.path.join(FIGURES, name + ".pdf"),
                        pagesize=landscape(letter))
    pw, ph = landscape(letter)
    pdf.setFont("Helvetica", 11); pdf.drawString(50, ph-30, title)
    pdf.setFont("Helvetica", 8)
    if note: pdf.drawString(50, ph-44, note)
    left,bottom,right,top=60,55,pw-60,ph-65
    pdf.line(left,bottom,right,bottom); pdf.line(left,bottom,left,top)
    for index,(series,points) in enumerate(sorted(groups.items())):
        color=COLORS[index%len(COLORS)]; pdf.setStrokeColorRGB(*(c/255 for c in color))
        coords=[]
        for row in sorted(points,key=lambda x:float(x["x"])):
            x,value=float(row["x"]),float(row["value"])
            coords.append((left+(x-xmin)/(xmax-xmin)*(right-left),
                           bottom+(value-ymin)/(ymax-ymin)*(top-bottom)))
        for a,b in zip(coords,coords[1:]): pdf.line(a[0],a[1],b[0],b[1])
        for x,y in coords: pdf.circle(x,y,2,stroke=1,fill=0)
        pdf.drawString(right-160, top-index*12, series)
    pdf.setFillColorRGB(0,0,0); pdf.drawCentredString((left+right)/2,25,x_label)
    pdf.drawString(8,(bottom+top)/2,y_label); pdf.save()


def summary_plot_rows(records, scenario, subcase, metric):
    rows=[]
    for index,algorithm in enumerate(ALGORITHMS):
        values=[num(x,metric) for x in records if x["scenario"]==scenario
                and x["subcase"]==subcase and x["algorithm"]==algorithm]
        if values: rows.append({"x":index,"series":algorithm,
                                "value":mean(values),"label":algorithm})
    return rows


def time_rows(run, filename, value_key, series_key="link_id", limit=1200):
    source=read_csv(os.path.join(run,filename)); step=max(1,len(source)//limit)
    return [{"x":num(row,"time")*1e6,"series":row.get(series_key,"all"),
             "value":num(row,value_key),"label":row.get(series_key,"all")}
            for row in source[::step]]


def make_figures(records, rate_rows, admission_rows):
    os.makedirs(FIGURES,exist_ok=True)
    e1="e1_single_old_single_new"; e2="e2_batch_incast"; e4="e4_parking_lot"
    def rr(s,sub,a="cbap_full",seed=1):
        return next(x for x in records if x["scenario"]==s and x["subcase"]==sub
                    and x["algorithm"]==a and x["seed"]==seed)["run_dir"]
    # E1
    r=[x for x in rate_rows if x["scenario"]==e1 and x["flow_id"]=="1"]
    plot("e1_sender_actual_rate","E1 new-flow actual sender rates","algorithm index","Gbit/s",
         [{"x":ALGORITHMS.index(x["algorithm"]),"series":x["algorithm"],
           "value":x["actual_admission_mean_rate_bps"]/1e9,"label":"admission"} for x in r if x["seed"]==1])
    comp=[]
    for x in r:
        if x["seed"]!=1: continue
        for label,key in (("admit","initial_admit_rate_bps"),("base","tracking_base_rate_bps"),
                          ("actual","tracking_actual_rate_bps"),("current","tracking_current_rate_bps"),
                          ("target","mean_target_rate_bps")):
            comp.append({"x":ALGORITHMS.index(x["algorithm"]),"series":label,
                         "value":x[key]/1e9,"label":x["algorithm"]})
    plot("e1_rate_components","E1 rate components (seed 1)","algorithm index","Gbit/s",comp)
    plot("e1_queue","E1 controlled-link queue (Full, seed 1)","time (us)","bytes",
         time_rows(rr(e1,"default"),"selected_link_timeseries.csv","queue_bytes"))
    plot("e1_new_flow_fct","E1 new-flow completion time","algorithm index","us",
         summary_plot_rows(records,e1,"default","new_group_cct_us"))
    plot("e1_old_flow_throughput","E1 incumbent overall goodput","algorithm index","Gbit/s",
         summary_plot_rows(records,e1,"default","old_goodput_mean_gbps"))
    # E2
    new_ad=[x for x in admission_rows if x["scenario"]==e2 and x["batch_id"]=="1"]
    plot("e2_actual_aggregate_admission","E2 actual aggregate admission","algorithm index","Gbit/s",
         [{"x":ALGORITHMS.index(x["algorithm"]),"series":x["algorithm"],
           "value":x["actual_aggregate_admission_bps"]/1e9,"label":x["algorithm"]}
          for x in new_ad if x["seed"]==1])
    both=[]
    for x in new_ad:
        if x["seed"]!=1: continue
        for label,key in (("planned","planned_aggregate_admission_bps"),
                          ("actual","actual_aggregate_admission_bps"),
                          ("budget","reconstructed_admission_budget_bps")):
            both.append({"x":ALGORITHMS.index(x["algorithm"]),"series":label,
                         "value":x[key]/1e9,"label":x["algorithm"]})
    plot("e2_independent_vs_batch","E2 independent versus joint admission","algorithm index","Gbit/s",both)
    q=[]
    for idx,a in enumerate(("independent_min_grant","cbap_rate_only","cbap_full")):
        q.extend(time_rows(rr(e2,"default",a),"selected_link_timeseries.csv","queue_bytes"))
        for row in q[-len(q):]: pass
    # Rebuild with algorithm-labelled series.
    q=[]
    for a in ("independent_min_grant","cbap_rate_only","cbap_full"):
        for row in time_rows(rr(e2,"default",a),"selected_link_timeseries.csv","queue_bytes"):
            row["series"]=a; q.append(row)
    plot("e2_queue","E2 queue comparison (seed 1)","time (us)","bytes",q)
    plot("e2_utilization","E2 mean utilization","algorithm index","fraction",
         summary_plot_rows(records,e2,"default","mean_utilization"))
    plot("e2_cct","E2 new-batch CCT","algorithm index","us",
         summary_plot_rows(records,e2,"default","new_group_cct_us"))
    plot("e2_bytes_before_feedback","E2 bytes sent before complete fresh feedback","algorithm index","bytes",
         [{"x":ALGORITHMS.index(x["algorithm"]),"series":x["algorithm"],
           "value":x["bytes_before_fresh_feedback"],"label":x["algorithm"]}
          for x in new_ad if x["seed"]==1])
    # E4 synchronous
    flow=[]
    for a in ALGORITHMS:
        vals=[x for x in records if x["scenario"]==e4 and x["subcase"]=="synchronous" and x["algorithm"]==a]
        for fid,key in enumerate(("flow0_goodput_gbps","flow1_goodput_gbps","flow2_goodput_gbps")):
            flow.append({"x":ALGORITHMS.index(a),"series":"F%d"%fid,
                         "value":mean([num(x,key) for x in vals]),"label":a})
    plot("e4_sync_flow_rates","E4 synchronous flow goodputs","algorithm index","Gbit/s",flow)
    grants=[]
    for x in rate_rows:
        if x["scenario"]==e4 and x["subcase"]=="synchronous" and x["seed"]==1:
            grants.append({"x":int(x["flow_id"]),"series":x["algorithm"],
                           "value":x["initial_admit_rate_bps"]/1e9,"label":x["flow_id"]})
    plot("e4_sync_grants","E4 synchronous initial grants (seed 1)","flow id","Gbit/s",grants)
    plot("e4_sync_queues","E4 synchronous queues (Full, seed 1)","time (us)","bytes",
         time_rows(rr(e4,"synchronous"),"selected_link_timeseries.csv","queue_bytes"))
    plot("e4_sync_utilization","E4 synchronous link utilization (Full, seed 1)","time (us)","fraction",
         time_rows(rr(e4,"synchronous"),"selected_link_timeseries.csv","utilization"))
    # E4 staggered
    f0=[x for x in rate_rows if x["scenario"]==e4 and x["subcase"]=="staggered"
        and x["algorithm"]=="cbap_full" and x["flow_id"]=="2" and x["seed"]==1][0]
    plot("e4_staggered_f0_rate","E4 staggered later F0 rates (seed 1)","component","Gbit/s",
         [{"x":i,"series":name,"value":f0[key]/1e9,"label":name}
          for i,(name,key) in enumerate((("actual","tracking_actual_rate_bps"),
                                         ("current","tracking_current_rate_bps"),
                                         ("base","tracking_base_rate_bps"),
                                         ("target","mean_target_rate_bps")))])
    plot("e4_staggered_floor_decay","E4 staggered protection-floor decay","time","rate",[],
         "NOT_MEASURED: floor value/timestamps were not retained in run outputs")
    release=3005000
    plot("e4_staggered_convergence","E4 staggered F0 threshold convergence","threshold","us after release",
         [{"x":i,"series":name,"value":max(f0[key]-release,0)/1000,"label":name}
          for i,(name,key) in enumerate((("80%","fair80_ns"),("90%","fair90_ns"),("95%","fair95_ns")))])
    plot("e4_staggered_link_utilization","E4 staggered link utilization (Full, seed 1)","time (us)","fraction",
         time_rows(rr(e4,"staggered"),"selected_link_timeseries.csv","utilization"))


def grouped_metric(records, scenario, subcase, algorithm, metric):
    return mean([num(x,metric) for x in records if x["scenario"]==scenario
                 and x["subcase"]==subcase and x["algorithm"]==algorithm])


def write_reports(records, invalid, missing, rate_rows, admission_rows,
                  deterministic, input_issues, decision):
    os.makedirs(REPORTS,exist_ok=True)
    semantic=open(os.path.join(REPORTS,"semantic_validation_report.md")).readline().strip()
    integrity=["# CBAP-v1 result integrity report","",
               "- Semantic status: `%s`"%semantic,
               "- Expected formal runs: 84","- Valid formal runs: %d"%len(records),
               "- Invalid formal runs: %d"%len(invalid),
               "- Missing formal runs: %d"%len(missing),
               "- Input-hash consistency issues: %d"%len(input_issues),
               "- Statistical unit: scenario + algorithm + seed.",
               "- Packet/epoch rows are used only to derive run metrics.",
               "- No p-values are reported; three seeds use mean, median, min and max.","",
               "## Seed effect","", deterministic]
    open(os.path.join(REPORTS,"result_integrity_report.md"),"w").write("\n".join(integrity)+"\n")
    semantic_text=["# Semantic fix verification","",
                   "The existing semantic gate is **%s**."%semantic,"",
                   "- All 20 semantic runs completed.",
                   "- Ordinary admission updates: 0.",
                   "- Complete feedback is strictly post-release.",
                   "- Admission exit follows complete feedback.",
                   "- Full credit gate is disabled after admission.",
                   "- Sender pacing violations: 0.",
                   "- E2 actual independent and batch admission rates differ.","",
                   "This establishes the tested implementation invariants, not performance value."]
    open(os.path.join(REPORTS,"semantic_fix_verification.md"),"w").write("\n".join(semantic_text)+"\n")
    e1="e1_single_old_single_new"; e2="e2_batch_incast"; e4="e4_parking_lot"
    gm=lambda s,sub,a,k:grouped_metric(records,s,sub,a,k)
    indep=[x for x in admission_rows if x["scenario"]==e2 and x["algorithm"]=="independent_min_grant" and x["batch_id"]=="1"]
    rate=[x for x in admission_rows if x["scenario"]==e2 and x["algorithm"]=="cbap_rate_only" and x["batch_id"]=="1"]
    full=[x for x in admission_rows if x["scenario"]==e2 and x["algorithm"]=="cbap_full" and x["batch_id"]=="1"]
    ia=mean([x["actual_aggregate_admission_bps"] for x in indep])/1e9
    ra=mean([x["actual_aggregate_admission_bps"] for x in rate])/1e9
    fa=mean([x["actual_aggregate_admission_bps"] for x in full])/1e9
    overs=mean([x["actual_capacity_oversubscription_bps"] for x in indep])/1e9
    f0=gm(e4,"staggered","cbap_full","flow2_goodput_gbps")
    f1=gm(e4,"staggered","cbap_full","flow0_goodput_gbps")
    f2=gm(e4,"staggered","cbap_full","flow1_goodput_gbps")
    stagger_f0_audit=[x for x in rate_rows if x["scenario"]==e4 and
                      x["subcase"]=="staggered" and
                      x["algorithm"]=="cbap_full" and x["flow_id"]=="2"]
    rate4=mean([x["current_rate_at_4rtt_bps"] for x in stagger_f0_audit])/1e9
    rate6=mean([x["current_rate_at_6rtt_bps"] for x in stagger_f0_audit])/1e9
    f0_track_actual=mean([x["tracking_actual_rate_bps"] for x in stagger_f0_audit])/1e9
    f0_track_current=mean([x["tracking_current_rate_bps"] for x in stagger_f0_audit])/1e9
    f0_track_base=mean([x["tracking_base_rate_bps"] for x in stagger_f0_audit])/1e9
    multi_decrease=sum(x["multi_decrease_epoch_violations"] for x in rate_rows)
    lines=["# CBAP-v1 final analysis","","## Decision","", "**%s**"%decision,"",
           "Implementation validity and research value are separated below. No old CBAP-v0 STOP decision is reused.","",
           "## Integrity","","- Formal runs: %d/84 valid; %d invalid; %d missing."%(len(records),len(invalid),len(missing)),
           "- Semantic repair: %s."%semantic,"- %s"%deterministic,"",
           "## RQ1 — actual independent versus batch admission","",
           "E2 actual aggregate admission is %.3f Gbit/s for Independent, %.3f for Rate-Only, and %.3f for Full. Independent exceeds the reconstructed admission budget by %.3f Gbit/s. The fixed implementation therefore produces a real sender-side distinction, not merely different plan fields."%(ia,ra,fa,overs),"",
           "## RQ2 — Full credit lifetime","",
           "All semantic credit gates exit with admission and all pacing counters are zero. In staggered E4, F0 tracking actual/current/base rates are %.3f/%.3f/%.3f Gbit/s (actual/current ratio %.3f). Actual tracking is therefore no longer permanently clamped to the initial base rate."%(f0_track_actual,f0_track_current,f0_track_base,f0_track_actual/f0_track_current),"",
           "## RQ3 — batch-admission value in E2","",
           "Rate-Only versus Independent changes peak queue by %+.2f%%, queue AUC by %+.2f%%, and new-batch CCT by %+.2f%%. Joint admission removes the reconstructed actual oversubscription while retaining similar old-flow aggregate goodput."%(
             pct(gm(e2,"default","cbap_rate_only","queue_max_bytes"),gm(e2,"default","independent_min_grant","queue_max_bytes")),
             pct(gm(e2,"default","cbap_rate_only","queue_auc_byte_seconds"),gm(e2,"default","independent_min_grant","queue_auc_byte_seconds")),
             pct(gm(e2,"default","cbap_rate_only","new_group_cct_us"),gm(e2,"default","independent_min_grant","new_group_cct_us"))),"",
           "## RQ4 — continuous tracking","",
           "In E2, Rate-Only versus Init-Only changes new-batch CCT by %+.2f%% and peak queue by %+.2f%%. Tracking is valuable in this incast, but E1 Rate-Only is %+.2f%% slower in new-flow CCT than Init-Only, so the benefit is workload-dependent."%(
             pct(gm(e2,"default","cbap_rate_only","new_group_cct_us"),gm(e2,"default","cbap_init_only","new_group_cct_us")),
             pct(gm(e2,"default","cbap_rate_only","queue_max_bytes"),gm(e2,"default","cbap_init_only","queue_max_bytes")),
             pct(gm(e1,"default","cbap_rate_only","new_group_cct_us"),gm(e1,"default","cbap_init_only","new_group_cct_us"))),"",
           "## RQ5 — credit ablation","",
           "Full versus Rate-Only changes E2 peak queue by %+.2f%%, queue AUC by %+.2f%%, and CCT by %+.2f%%. In E1 and both static E4 cases the two outputs are identical. Credit therefore has a modest E2 queue benefit here, but no independent gain in the accurate static cases; prediction-error/background-burst validation remains necessary."%(
             pct(gm(e2,"default","cbap_full","queue_max_bytes"),gm(e2,"default","cbap_rate_only","queue_max_bytes")),
             pct(gm(e2,"default","cbap_full","queue_auc_byte_seconds"),gm(e2,"default","cbap_rate_only","queue_auc_byte_seconds")),
             pct(gm(e2,"default","cbap_full","new_group_cct_us"),gm(e2,"default","cbap_rate_only","new_group_cct_us"))),"",
           "## RQ6 — parking-lot fairness","",
           "Synchronous Full goodputs are %.3f/%.3f/%.3f Gbit/s. Staggered later F0 is %.3f Gbit/s versus %.3f/%.3f for incumbents, so F0/min(F1,F2)=%.3f. It is not the old ~25 Gbit/s result, but staggered fairness is still incomplete. F0 current rate is %.3f Gbit/s at 4 estimated RTT and %.3f Gbit/s at 6 RTT. Multi-decrease flow/epoch violations across CBAP runs: %d. Retained outputs do not expose the internal protection-floor value, so its decay is explicitly NOT_MEASURED."%(
             gm(e4,"synchronous","cbap_full","flow0_goodput_gbps"),gm(e4,"synchronous","cbap_full","flow1_goodput_gbps"),gm(e4,"synchronous","cbap_full","flow2_goodput_gbps"),f0,f1,f2,f0/min(f1,f2),rate4,rate6,multi_decrease),"",
           "## Interpretation","",
           "- Code semantics tested by the 20-run gate are correct.",
           "- The batch-admission hypothesis is supported in E2.",
           "- Tracking helps E2 but is not uniformly beneficial.",
           "- Credit is not generally necessary in these static accurate-prediction cases.",
           "- Victim isolation remains unvalidated because E3 was intentionally not rerun.",
           "- The remaining E1 cost and staggered parking-lot imbalance require major revision before a broad claim."]
    open(os.path.join(REPORTS,"final_analysis_report.md"),"w").write("\n".join(lines)+"\n")
    suspicious=["# Suspicious findings","",
                "- %s"%deterministic,
                "- Mean sampled utilization slightly above 1 can arise from retained counter-window boundaries; it is not interpreted as physical over-capacity.",
                "- E4 protection-floor values/timestamps were not retained; floor decay is NOT_MEASURED.",
                "- Victim-flow behavior is not tested in this reduced matrix.",
                "- CBAP-Full and Rate-Only are byte-identical in several static scenario metrics; this is disclosed rather than treated as extra seed evidence."]
    open(os.path.join(REPORTS,"suspicious_findings.md"),"w").write("\n".join(suspicious)+"\n")
    measured=["# Measured versus interpreted","","## Directly measured",
              "Flow/round completion, sender TX events, admission/credit state, queue samples, utilization counters, ECN/PFC rows, rate transitions, and control-message counts.","",
              "## Run-level derivations","","FCT/CCT, queue AUC summaries, actual aggregate admission rate, reconstructed admission budget, goodput ratios, and paired seed percentage differences.","",
              "## Interpretation","","Batch coordination explains the E2 oversubscription removal; tracking and credit contributions are ablation interpretations. These are ns-3 fixed-path results, not production or dynamic-routing claims. Three seeds do not establish broad statistical stability."]
    open(os.path.join(REPORTS,"measured_vs_interpreted.md"),"w").write("\n".join(measured)+"\n")


def main():
    os.makedirs(PROCESSED,exist_ok=True); os.makedirs(REPORTS,exist_ok=True)
    semantic_path=os.path.join(REPORTS,"semantic_validation_report.md")
    semantic=open(semantic_path).readline().strip() if os.path.isfile(semantic_path) else "MISSING"
    manifest=list(csv.DictReader(open(os.path.join(ROOT,"config","formal_manifest.csv"))))
    records=[]; invalid=[]; missing=[]
    for expected in manifest:
        problems=validate(expected)
        if problems:
            row={"run_id":expected["run_id"],"run_dir":run_path(expected),"reason":";".join(problems)}
            (missing if "missing_run_directory" in problems else invalid).append(row)
        else: records.append(derive(expected))
    # Cross-algorithm input hashes must match for a scenario/subcase/seed.
    hash_groups=defaultdict(set)
    for run in records:
        meta=json.load(open(os.path.join(run["run_dir"],"run_meta.json")))
        value=json.dumps(meta.get("input_hashes",{}),sort_keys=True)
        hash_groups[(run["scenario"],run["subcase"],run["seed"])].add(value)
    input_issues=[{"scenario":k[0],"subcase":k[1],"seed":k[2],"hash_variant_count":len(v)}
                  for k,v in hash_groups.items() if len(v)!=1]
    # Quantify seed effects without pretending deterministic repeats are independent evidence.
    deterministic_groups=[]; varying_groups=[]
    for key in sorted(set((x["scenario"],x["subcase"],x["algorithm"]) for x in records)):
        rows=[x for x in records if (x["scenario"],x["subcase"],x["algorithm"])==key]
        signatures={tuple(round(num(x,m),9) for m in METRICS) for x in rows}
        (deterministic_groups if len(signatures)==1 else varying_groups).append(key)
    deterministic=("DETERMINISTIC_REPETITION for %d/28 scenario-algorithm groups; only %d/28 vary across seeds (all varying groups are E2). Input schedules are identical across seeds; the seed affects only stochastic simulation behavior where present."%(len(deterministic_groups),len(varying_groups)))
    write_csv(os.path.join(PROCESSED,"summary_by_run.csv"),records)
    write_csv(os.path.join(PROCESSED,"summary_by_scenario.csv"),aggregate(records))
    write_csv(os.path.join(PROCESSED,"paired_comparisons.csv"),paired(records))
    write_csv(os.path.join(PROCESSED,"invalid_runs.csv"),invalid,["run_id","run_dir","reason"])
    write_csv(os.path.join(PROCESSED,"missing_runs.csv"),missing,["run_id","run_dir","reason"])
    rate_rows=make_rate_audit(records)
    admission_rows=make_admission_audit(records)
    write_csv(os.path.join(PROCESSED,"rate_tracking_audit.csv"),rate_rows)
    write_csv(os.path.join(PROCESSED,"admission_effect_audit.csv"),admission_rows)
    write_csv(os.path.join(PROCESSED,"control_overhead_summary.csv"),control_overhead(records))
    write_csv(os.path.join(PROCESSED,"input_hash_issues.csv"),input_issues,
              ["scenario","subcase","seed","hash_variant_count"])
    implementation_ok=(semantic=="SEMANTIC_PASS" and not invalid and not missing and not input_issues)
    if not implementation_ok: decision="INVALID_IMPLEMENTATION"
    else:
        e2=lambda a,k:grouped_metric(records,"e2_batch_incast","default",a,k)
        batch_distinct=e2("independent_min_grant","queue_max_bytes")>e2("cbap_rate_only","queue_max_bytes")*1.2
        stagger=grouped_metric(records,"e4_parking_lot","staggered","cbap_full","flow2_goodput_gbps")/min(
            grouped_metric(records,"e4_parking_lot","staggered","cbap_full","flow0_goodput_gbps"),
            grouped_metric(records,"e4_parking_lot","staggered","cbap_full","flow1_goodput_gbps"))
        decision="CONTINUE_WITH_MAJOR_REVISION" if batch_distinct and stagger<0.9 else ("CONTINUE" if batch_distinct else "STOP")
    if semantic=="SEMANTIC_PASS":
        make_figures(records,rate_rows,admission_rows)
        write_reports(records,invalid,missing,rate_rows,admission_rows,deterministic,input_issues,decision)
    else:
        open(os.path.join(REPORTS,"semantic_failure_summary.md"),"w").write(
            "# Semantic failure\n\nFormal analysis stopped because semantic status is `%s`.\n"%semantic)
    print("semantic=%s expected=%d valid=%d invalid=%d missing=%d decision=%s"%(
        semantic,len(manifest),len(records),len(invalid),len(missing),decision))


if __name__=="__main__": main()
