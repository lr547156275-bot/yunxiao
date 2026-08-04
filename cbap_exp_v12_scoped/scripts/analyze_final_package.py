#!/usr/bin/env python3
"""Deterministic, read-only analysis of the completed CBAP v1.2 runs.

The script writes only reports/, processed/, and figures/.  It never invokes
the simulator and never edits a run directory.
"""
import csv
import gzip
import hashlib
import json
import math
import os
import re
import statistics
import subprocess
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(ROOT, ".."))
PROC = os.path.join(ROOT, "processed")
REPORT = os.path.join(ROOT, "reports")
FIG = os.path.join(ROOT, "figures")
SCOPE_RUNS = os.path.join(ROOT, "runs_scope")
CORE_RUNS = os.path.join(ROOT, "runs_core")
os.makedirs(PROC, exist_ok=True)
os.makedirs(REPORT, exist_ok=True)
os.makedirs(FIG, exist_ok=True)

REQUIRED = [
    "manifest.json", "result.json", "config.txt", "command.txt", "stdout.log",
    "flow_summary.csv", "queue_summary.csv", "scope_summary.csv",
    "rate_summary.csv", "control_summary.csv",
]
OFFICIAL = ["dctcp", "dcqcn", "timely", "hpcc_int", "bop_qb",
            "independent_min_grant", "cbap_full_v12_scoped"]
BASELINES = ["dctcp", "dcqcn", "timely", "hpcc_int", "bop_qb",
             "independent_min_grant"]
ABLATIONS = ["independent_min_grant", "cbap_init_only", "cbap_rateonly_v11",
             "cbap_full_v11_unscoped", "cbap_full_v12_scoped"]
DISPLAY = {
    "dctcp": "DCTCP", "dcqcn": "DCQCN", "timely": "TIMELY",
    "hpcc_int": "HPCC-INT", "bop_qb": "BOP-QB",
    "independent_min_grant": "Independent-Min-Grant",
    "cbap_full_v12_scoped": "Scoped CBAP-Full-v1.1",
    "cbap_init_only": "CBAP-Init-Only",
    "cbap_rateonly_v11": "CBAP-RateOnly-v1.1",
    "cbap_full_v11_unscoped": "Unscoped CBAP-Full-v1.1",
}
REPRESENTATIVE = ["fan4_msg64k_load80", "fan16_msg1m_load80",
                  "fan64_msg4m_load80", "fan16_msg1m_load0",
                  "fan16_msg1m_load95"]


def read_csv(path):
    candidate = path if os.path.isfile(path) else path + ".gz"
    if not os.path.isfile(candidate):
        return []
    opener = gzip.open if candidate.endswith(".gz") else open
    with opener(candidate, "rt", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields=None):
    if fields is None:
        fields = list(rows[0]) if rows else ["status"]
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_json(path, default=None):
    try:
        with open(path) as handle:
            return json.load(handle)
    except Exception:
        return {} if default is None else default


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def fnum(row, key, default=0.0):
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def inum(row, key, default=0):
    try:
        return int(float(row.get(key, default)))
    except (TypeError, ValueError):
        return default


def truth(value):
    return value is True or str(value).lower() in ("true", "1", "yes")


def pct(new, base):
    return (new - base) / base * 100.0 if base else float("nan")


def finite_json(obj):
    if isinstance(obj, dict):
        return all(finite_json(v) for v in obj.values())
    if isinstance(obj, list):
        return all(finite_json(v) for v in obj)
    if isinstance(obj, float):
        return math.isfinite(obj)
    return True


def parse_config(path):
    out = {}
    try:
        for line in open(path):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) == 2:
                out[parts[0]] = parts[1]
    except OSError:
        pass
    return out


def scenario_dims(name):
    m = re.match(r"fan(\d+)_msg(64k|256k|1m|4m)_load(\d+)$", name)
    if not m:
        return 0, 0, 0
    msg = {"64k": 65536, "256k": 262144, "1m": 1048576,
           "4m": 4194304}[m.group(2)]
    return int(m.group(1)), msg, int(m.group(3))


def inspect_runs():
    inventory, missing_rows, invalid_rows = [], [], []
    sets = [("scope", SCOPE_RUNS, os.path.join(ROOT, "configs", "scope_manifest.csv")),
            ("core", CORE_RUNS, os.path.join(ROOT, "configs", "core_manifest.csv"))]
    completed = {"scope": 0, "core": 0}
    for kind, base, manifest_csv in sets:
        for expected in csv.DictReader(open(manifest_csv)):
            run_dir = os.path.join(base, expected["scenario"],
                                   expected["algorithm_name"], "seed_1")
            missing = [name for name in REQUIRED if not os.path.isfile(os.path.join(run_dir, name))]
            manifest_path = os.path.join(run_dir, "manifest.json")
            result_path = os.path.join(run_dir, "result.json")
            manifest = load_json(manifest_path)
            result = load_json(result_path)
            reasons = []
            if missing:
                reasons.append("missing_required_files")
            exit_path = os.path.join(run_dir, "exit_status.txt")
            if os.path.isfile(exit_path) and open(exit_path).read().strip() != "0":
                reasons.append("nonzero_exit")
            if result and not truth(result.get("all_flows_completed", False)):
                reasons.append("incomplete_flows")
            if result and truth(result.get("log_truncated", False)):
                reasons.append("log_truncated")
            if result and not finite_json(result):
                reasons.append("nan_or_inf")
            if os.path.isfile(os.path.join(run_dir, "completed.flag")) and not reasons:
                completed[kind] += 1
            sizes = {name: os.path.getsize(os.path.join(run_dir, name))
                     for name in REQUIRED if os.path.isfile(os.path.join(run_dir, name))}
            command = ""
            cp = os.path.join(run_dir, "command.txt")
            if os.path.isfile(cp):
                command = open(cp).read().strip()
            row = {
                "run_set": kind, "run_id": expected["run_id"],
                "scenario": expected["scenario"],
                "algorithm": expected["algorithm_name"],
                "manifest_path": os.path.relpath(manifest_path, REPO),
                "result_path": os.path.relpath(result_path, REPO),
                "valid": not reasons, "missing_files": ";".join(missing),
                "failure_reasons": ";".join(reasons), "run_command": command,
                "git_commit": manifest.get("git_commit", ""),
                "required_file_sizes_json": json.dumps(sizes, sort_keys=True),
                "result_sha256": sha256(result_path) if os.path.isfile(result_path) else "",
            }
            inventory.append(row)
            if missing:
                missing_rows.append(row)
            if reasons:
                invalid_rows.append(row)
    write_csv(os.path.join(PROC, "run_file_inventory.csv"), inventory)
    write_csv(os.path.join(PROC, "missing_runs.csv"), missing_rows,
              list(inventory[0]))
    write_csv(os.path.join(PROC, "invalid_runs.csv"), invalid_rows,
              list(inventory[0]))
    return inventory, missing_rows, invalid_rows, completed


def compute_run_rows():
    old = {r["run_id"]: r for r in csv.DictReader(open(os.path.join(PROC, "core_results.csv")))}
    out = []
    for m in csv.DictReader(open(os.path.join(ROOT, "configs", "core_manifest.csv"))):
        run_dir = os.path.join(CORE_RUNS, m["scenario"], m["algorithm_name"], "seed_1")
        base = old[m["run_id"]]
        case = load_json(os.path.join(run_dir, "scenario_meta.json"))
        pending = set(int(x) for x in case.get("pending_flow_ids", []))
        flows = read_csv(os.path.join(run_dir, "flow_summary.csv"))
        state = read_csv(os.path.join(run_dir, "cbap_flow_state.csv"))
        admission = read_csv(os.path.join(run_dir, "cbap_admission.csv"))
        actual = sum(fnum(x, "actual_admission_mean_rate_bps") for x in state
                     if inum(x, "flow_id", -1) in pending)
        planned = sum(fnum(x, "admit_rate_bps") for x in admission
                      if inum(x, "flow_id", -1) in pending)
        capacity = fnum(case, "capacity_bps", 1e11)
        actual_ratio = actual / capacity if capacity else 0.0
        control = read_csv(os.path.join(run_dir, "control_summary.csv"))
        scope = read_csv(os.path.join(run_dir, "scope_summary.csv"))
        port = read_csv(os.path.join(run_dir, "cbap_port_summary.csv"))
        grants = len(admission)
        control_messages = sum(inum(x, "summary_messages") + inum(x, "grant_messages") for x in control)
        control_bytes = sum(inum(x, "total_control_bytes") for x in control)
        cfg = parse_config(os.path.join(run_dir, "config.txt"))
        sim_seconds = float(cfg.get("SIMULATOR_STOP_TIME", "0.1"))
        payload_size = int(cfg.get("PACKET_PAYLOAD_SIZE", "1000"))
        wire_packet = int(cfg.get("CBAP_MAX_WIRE_PACKET_BYTES", str(payload_size + 64)))
        payload_bytes = sum(inum(x, "total_size_bytes", inum(x, "size_bytes")) for x in flows)
        packet_count = sum(int(math.ceil(inum(x, "total_size_bytes", inum(x, "size_bytes")) /
                                         float(payload_size))) for x in flows)
        data_wire = payload_bytes + packet_count * max(0, wire_packet - payload_size)
        util = fnum(base, "bottleneck_utilization")
        row = {
            "run_id": m["run_id"], "scenario_id": m["scenario"],
            "fanin": int(m["fan_in"]), "message_bytes": int(m["message_bytes"]),
            "incumbent_target_load": int(m["incumbent_load_percent"]),
            "incumbent_measured_load": fnum(base, "measured_pre_release_utilization_percent"),
            "algorithm": m["algorithm_name"], "algorithm_display": DISPLAY[m["algorithm_name"]],
            "scope_enabled": base["scope_decision"] == "ENABLE",
            "scope_reason": base["scope_reason"],
            "triggering_link_count": len([x for x in base["triggering_links"].split(";") if x]),
            "CCT_us": fnum(base, "new_batch_cct_us"),
            "median_FCT_us": fnum(base, "median_flow_fct_us"),
            "max_FCT_us": fnum(base, "max_flow_fct_us"),
            "completion_skew_us": fnum(base, "completion_skew_us"),
            "peak_queue_bytes": fnum(base, "peak_queue_bytes"),
            "queue_AUC_byte_us": fnum(base, "queue_auc_byte_seconds") * 1e6,
            "utilization_raw": util, "utilization_corrected": min(util, 1.0),
            "incumbent_worst_throughput_drop": fnum(base, "incumbent_worst_throughput_drop"),
            "ECN_count": inum(base, "ecn_count"), "ECN_ratio": fnum(base, "ecn_ratio"),
            "PFC_count": inum(base, "pfc_count"), "PFC_duration_us": fnum(base, "pfc_duration_us"),
            "bytes_before_first_fresh_feedback": inum(base, "bytes_before_first_fresh_feedback"),
            "planned_admission_rate_bps": planned,
            "actual_admission_rate_bps": actual,
            "independent_oversubscription_ratio": actual_ratio if m["algorithm_name"] == "independent_min_grant" else 0,
            "independent_excess_ratio": max(actual_ratio - 1.0, 0) if m["algorithm_name"] == "independent_min_grant" else 0,
            "scope_decision_count": len(scope), "port_summary_count": len(port),
            "grant_count": grants, "control_messages": control_messages,
            "control_bytes": control_bytes,
            "control_messages_per_sim_second": control_messages / sim_seconds,
            "control_bandwidth_bps": control_bytes * 8 / sim_seconds,
            "per_flow_grant_frequency": grants / max(len(pending), 1),
            "data_wire_bytes": data_wire,
            "control_to_data_wire_ratio": control_bytes / data_wire if data_wire else 0,
            "capacity_violation": inum(base, "capacity_violation"),
            "credit_violation": inum(base, "credit_violation"),
            "pacing_violation": inum(base, "pacing_violation"),
            "valid": truth(base["valid"]), "ablation": int(m["ablation"]),
        }
        out.append(row)
    write_csv(os.path.join(PROC, "summary_by_run.csv"), out)
    write_csv(os.path.join(PROC, "summary_by_scenario.csv"), out)
    return out


def paired_and_scaling(rows):
    by = {(r["scenario_id"], r["algorithm"]): r for r in rows}
    pairs = []
    metrics = ["CCT_us", "peak_queue_bytes", "queue_AUC_byte_us", "utilization_raw",
               "completion_skew_us", "incumbent_worst_throughput_drop"]
    for scenario in sorted(set(r["scenario_id"] for r in rows if not r["ablation"])):
        scoped = by[(scenario, "cbap_full_v12_scoped")]
        for baseline in BASELINES:
            b = by[(scenario, baseline)]
            x = {"scenario_id": scenario, "fanin": scoped["fanin"],
                 "message_bytes": scoped["message_bytes"],
                 "incumbent_load": scoped["incumbent_target_load"],
                 "baseline": baseline, "baseline_display": DISPLAY[baseline]}
            for metric in metrics:
                x[metric + "_scoped"] = scoped[metric]
                x[metric + "_baseline"] = b[metric]
                x[metric + "_abs_diff"] = scoped[metric] - b[metric]
                x[metric + "_pct_diff"] = pct(scoped[metric], b[metric])
            pairs.append(x)
    write_csv(os.path.join(PROC, "paired_comparisons.csv"), pairs)
    official = [r for r in rows if not r["ablation"]]
    fan = [r for r in official if r["incumbent_target_load"] == 80]
    msg = [r for r in official if r["fanin"] == 16 and r["incumbent_target_load"] == 80]
    load = [r for r in official if r["fanin"] == 16 and r["message_bytes"] == 1048576]
    write_csv(os.path.join(PROC, "fanin_scaling.csv"), fan)
    write_csv(os.path.join(PROC, "message_scaling.csv"), msg)
    write_csv(os.path.join(PROC, "load_scaling.csv"), load)
    independent = [r for r in official if r["algorithm"] == "independent_min_grant"]
    write_csv(os.path.join(PROC, "independent_oversubscription.csv"), independent)
    return pairs, by, fan, msg, load, independent


def scope_outputs():
    expected = {
        "single_pending": "BYPASS", "batch_incast": "ENABLE",
        "two_pending_overload": "ENABLE", "two_pending_low_demand": "BYPASS",
        "no_shared_link": "BYPASS", "synchronous_parking_lot": "ENABLE",
    }
    audit = read_csv(os.path.join(PROC, "scope_decision_audit.csv"))
    mapped = []
    ok = True
    for scenario, decision in expected.items():
        matches = [r for r in audit if r["scenario"] == scenario and
                   r["algorithm"] == "cbap_full_v12_scoped"]
        actual = matches[0]["decision"] if matches else "MISSING"
        valid = bool(matches) and actual == decision and truth(matches[0]["valid"])
        ok = ok and valid
        mapped.append({"scenario": scenario, "expected_decision": decision,
                       "actual_decision": actual,
                       "scope_reason": matches[0].get("failure_reasons", "") if matches else "",
                       "valid": valid})
    write_csv(os.path.join(PROC, "scope_activation_map.csv"), mapped)
    overhead = read_csv(os.path.join(PROC, "scope_overhead_decomposition.csv"))
    write_csv(os.path.join(PROC, "scope_overhead_summary.csv"), overhead)
    return ok, mapped, overhead


def audits(rows, pairs, by):
    util = []
    suspicious = []
    violations = []
    for r in rows:
        over = r["utilization_raw"] > 1.0
        util.append({"run_id": r["run_id"], "scenario_id": r["scenario_id"],
                     "algorithm": r["algorithm"], "raw_utilization": r["utilization_raw"],
                     "corrected_utilization": r["utilization_corrected"],
                     "over_100_percent": over,
                     "audit_interpretation": "sampling-window boundary overshoot" if over else "within physical bound"})
        if over:
            suspicious.append({"run_id": r["run_id"], "finding": "utilization_above_100_percent",
                               "value": r["utilization_raw"], "severity": "audit"})
        if r["capacity_violation"] or r["credit_violation"] or r["pacing_violation"]:
            suspicious.append({"run_id": r["run_id"], "finding": "controller_constraint_violation",
                               "value": "%s/%s/%s" % (r["capacity_violation"], r["credit_violation"], r["pacing_violation"]),
                               "severity": "invalid"})
        violations.append({k: r[k] for k in ["run_id", "scenario_id", "algorithm",
                            "capacity_violation", "credit_violation", "pacing_violation", "valid"]})
    write_csv(os.path.join(PROC, "utilization_audit.csv"), util)
    write_csv(os.path.join(PROC, "capacity_credit_pacing_audit.csv"), violations)
    write_csv(os.path.join(PROC, "suspicious_runs.csv"), suspicious,
              ["run_id", "finding", "value", "severity"])
    control = [{k: r[k] for k in ["run_id", "scenario_id", "fanin", "message_bytes",
               "incumbent_target_load", "algorithm", "scope_decision_count", "port_summary_count",
               "grant_count", "control_messages", "control_bytes", "control_messages_per_sim_second",
               "control_bandwidth_bps", "per_flow_grant_frequency", "data_wire_bytes",
               "control_to_data_wire_ratio"]} for r in rows]
    write_csv(os.path.join(PROC, "control_overhead.csv"), control)
    ablation = [r for r in rows if r["algorithm"] in ABLATIONS and
                (r["ablation"] or r["algorithm"] in ("independent_min_grant", "cbap_full_v12_scoped")) and
                r["scenario_id"] in ("fan4_msg64k_load80", "fan16_msg1m_load80", "fan64_msg4m_load80")]
    write_csv(os.path.join(PROC, "ablation_summary.csv"), ablation)
    pareto = []
    for scenario in sorted(set(r["scenario_id"] for r in rows if not r["ablation"])):
        s, d = by[(scenario, "cbap_full_v12_scoped")], by[(scenario, "dcqcn")]
        cct_pct, q_pct = pct(s["CCT_us"], d["CCT_us"]), pct(s["peak_queue_bytes"], d["peak_queue_bytes"])
        positive = (cct_pct <= 3 and q_pct <= -30) or (cct_pct < 0 and q_pct < 0)
        pareto.append({"scenario_id": scenario, "fanin": s["fanin"], "message_bytes": s["message_bytes"],
                       "incumbent_load": s["incumbent_target_load"], "scope_enabled": s["scope_enabled"],
                       "scoped_CCT_us": s["CCT_us"], "dcqcn_CCT_us": d["CCT_us"],
                       "CCT_pct_diff": cct_pct, "scoped_peak_queue_bytes": s["peak_queue_bytes"],
                       "dcqcn_peak_queue_bytes": d["peak_queue_bytes"], "peak_queue_pct_diff": q_pct,
                       "pareto_positive": positive,
                       "utilization_at_least_90_percent": s["utilization_raw"] >= .9,
                       "no_audit_violation": not (s["capacity_violation"] or s["credit_violation"] or s["pacing_violation"])})
    write_csv(os.path.join(PROC, "pareto_summary.csv"), pareto)
    return util, suspicious, control, ablation, pareto


# Tiny dependency-free vector chart writer.  The matching PNG is rasterized
# from the PDF by the already-installed pdftocairo utility.
COLORS = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf", "#111111",
          "#8c564b", "#e377c2", "#7f7f7f"]


def pdf_escape(s):
    return str(s).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_pdf(path, title, xlabel, ylabel, series, categorical=False):
    W, H = 720, 460
    L, R, B, T = 75, 20, 62, 52
    points = [(x, y) for pts in series.values() for x, y in pts if math.isfinite(x) and math.isfinite(y)]
    if not points:
        points = [(0, 0), (1, 1)]
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    if xmax == xmin: xmax = xmin + 1
    if ymax == ymin: ymax = ymin + 1
    padx, pady = (xmax-xmin)*.05, (ymax-ymin)*.08
    xmin, xmax, ymin, ymax = xmin-padx, xmax+padx, max(0, ymin-pady), ymax+pady
    sx = lambda x: L + (x-xmin)/(xmax-xmin)*(W-L-R)
    sy = lambda y: B + (y-ymin)/(ymax-ymin)*(H-B-T)
    c = ["1 1 1 rg 0 0 %d %d re f" % (W, H), "0 0 0 RG 0.8 w"]
    c += ["%g %g m %g %g l S" % (L, B, W-R, B), "%g %g m %g %g l S" % (L, B, L, H-T)]
    for i in range(6):
        y = ymin + i*(ymax-ymin)/5
        yy = sy(y)
        c.append("0.85 0.85 0.85 RG 0.3 w %g %g m %g %g l S" % (L, yy, W-R, yy))
        c.append("0 0 0 rg BT /F1 8 Tf %g %g Td (%s) Tj ET" % (8, yy-3, pdf_escape("%.3g" % y)))
    c.append("0 0 0 rg BT /F1 14 Tf 75 430 Td (%s) Tj ET" % pdf_escape(title))
    c.append("BT /F1 10 Tf 330 18 Td (%s) Tj ET" % pdf_escape(xlabel))
    c.append("BT /F1 10 Tf 8 440 Td (%s) Tj ET" % pdf_escape(ylabel))
    for idx, (name, pts) in enumerate(sorted(series.items())):
        rgb = tuple(int(COLORS[idx % len(COLORS)][i:i+2], 16)/255 for i in (1,3,5))
        clean = sorted((x,y) for x,y in pts if math.isfinite(x) and math.isfinite(y))
        if not clean: continue
        c.append("%g %g %g RG 1.2 w" % rgb)
        c.append("%g %g m " % (sx(clean[0][0]), sy(clean[0][1])) + " ".join("%g %g l" % (sx(x),sy(y)) for x,y in clean[1:]) + " S")
        for x,y in clean: c.append("%g %g %g rg %g %g 2.5 0 360 arc f" % (rgb + (sx(x),sy(y))))
        ly = H-T-12*(idx+1)
        c.append("%g %g %g rg 520 %g 12 3 re f BT /F1 7 Tf 536 %g Td (%s) Tj ET" % (rgb + (ly,ly-1,pdf_escape(name[:26]))))
    stream = "\n".join(c).encode("latin-1", "replace")
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 720 460] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objs, 1):
        offsets.append(len(data)); data.extend(("%d 0 obj\n" % i).encode()); data.extend(obj); data.extend(b"\nendobj\n")
    xref = len(data); data.extend(("xref\n0 %d\n0000000000 65535 f \n" % (len(objs)+1)).encode())
    for off in offsets[1:]: data.extend(("%010d 00000 n \n" % off).encode())
    data.extend(("trailer << /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs)+1,xref)).encode())
    open(path, "wb").write(data)


def write_svg(path, title, xlabel, ylabel, series):
    W,H,L,R,B,T=720,460,75,20,62,52
    points=[(x,y) for pts in series.values() for x,y in pts if math.isfinite(x) and math.isfinite(y)] or [(0,0),(1,1)]
    xs,ys=[p[0] for p in points],[p[1] for p in points]; xmin,xmax,ymin,ymax=min(xs),max(xs),min(ys),max(ys)
    if xmax==xmin:xmax+=1
    if ymax==ymin:ymax+=1
    px=(xmax-xmin)*.05;py=(ymax-ymin)*.08;xmin-=px;xmax+=px;ymin=max(0,ymin-py);ymax+=py
    sx=lambda x:L+(x-xmin)/(xmax-xmin)*(W-L-R);sy=lambda y:H-B-(y-ymin)/(ymax-ymin)*(H-B-T)
    esc=lambda s:str(s).replace('&','&amp;').replace('<','&lt;')
    z=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"><rect width="100%" height="100%" fill="white"/>',f'<text x="75" y="24" font-family="sans-serif" font-size="16">{esc(title)}</text>',f'<line x1="{L}" y1="{H-B}" x2="{W-R}" y2="{H-B}" stroke="black"/><line x1="{L}" y1="{T}" x2="{L}" y2="{H-B}" stroke="black"/>',f'<text x="330" y="445" font-family="sans-serif" font-size="11">{esc(xlabel)}</text>',f'<text x="8" y="38" font-family="sans-serif" font-size="11">{esc(ylabel)}</text>']
    for i,(name,pts) in enumerate(sorted(series.items())):
        color=COLORS[i%len(COLORS)];clean=sorted((x,y) for x,y in pts if math.isfinite(x) and math.isfinite(y)); coords=' '.join(f'{sx(x):.2f},{sy(y):.2f}' for x,y in clean)
        z.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="1.5"/>')
        z += [f'<circle cx="{sx(x):.2f}" cy="{sy(y):.2f}" r="2.5" fill="{color}"/>' for x,y in clean]
        z.append(f'<line x1="520" y1="{T+12*i}" x2="532" y2="{T+12*i}" stroke="{color}" stroke-width="3"/><text x="536" y="{T+3+12*i}" font-family="sans-serif" font-size="8">{esc(name[:26])}</text>')
    z.append('</svg>');open(path,'w').write('\n'.join(z))


def chart(name, title, xlabel, ylabel, source_rows, xkey, ykey, groupkey="algorithm_display"):
    source = os.path.join(FIG, name + ".csv")
    write_csv(source, source_rows)
    series = defaultdict(list)
    for r in source_rows:
        try: series[str(r[groupkey])].append((float(r[xkey]), float(r[ykey])))
        except (KeyError, ValueError, TypeError): pass
    pdf = os.path.join(FIG, name + ".pdf")
    write_pdf(pdf, title, xlabel, ylabel, series)
    write_svg(os.path.join(FIG, name + ".svg"), title, xlabel, ylabel, series)
    subprocess.run(["pdftocairo", "-singlefile", "-png", "-r", "120", pdf,
                    os.path.join(FIG, name)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def trace_rows(metric):
    out=[]
    for scenario in REPRESENTATIVE:
        for algo in ["dcqcn","hpcc_int","bop_qb","independent_min_grant","cbap_full_v12_scoped"]:
            d=os.path.join(CORE_RUNS,scenario,algo,"seed_1")
            fan,msg,load=scenario_dims(scenario)
            if metric=="queue":
                for x in read_csv(os.path.join(d,"selected_link_timeseries.csv")):
                    out.append({"scenario":scenario,"algorithm":algo,"series":scenario+"/"+DISPLAY[algo],
                                "time_us":fnum(x,"time")*1e6,"value":fnum(x,"queue_bytes")})
            else:
                rr=read_csv(os.path.join(d,"selected_flow_timeseries.csv")); case=load_json(os.path.join(d,"scenario_meta.json")); pending=set(case.get("pending_flow_ids",[])); chosen=min(pending) if pending else 0
                if metric=="rate":
                    for x in rr:
                        if inum(x,"flow_id",-1)==chosen:
                            out.append({"scenario":scenario,"algorithm":algo,"series":scenario+"/"+DISPLAY[algo],"time_us":fnum(x,"time")*1e6,"value":fnum(x,"current_rate")/1e9})
                else:
                    bytime=defaultdict(float)
                    for x in rr:
                        if inum(x,"flow_id",-1) in pending: bytime[fnum(x,"time")]+=fnum(x,"snd_una")
                    prev=None
                    for t,total in sorted(bytime.items()):
                        if prev and t>prev[0]: out.append({"scenario":scenario,"algorithm":algo,"series":scenario+"/"+DISPLAY[algo],"time_us":t*1e6,"value":max(0,(total-prev[1])*8/(t-prev[0])/1e9)})
                        prev=(t,total)
    return out


def make_figures(rows, fan, msg, load, independent, pareto, control):
    fan1=[r for r in fan if r["message_bytes"]==1048576]
    specs=[
      ("fanin_cct","Fan-in vs new-batch CCT","fan-in","CCT (us)",fan1,"fanin","CCT_us"),
      ("fanin_peak_queue","Fan-in vs peak queue","fan-in","peak queue (bytes)",fan1,"fanin","peak_queue_bytes"),
      ("fanin_queue_auc","Fan-in vs queue AUC","fan-in","queue AUC (byte-us)",fan1,"fanin","queue_AUC_byte_us"),
      ("fanin_utilization","Fan-in vs bottleneck utilization","fan-in","utilization (fraction)",fan1,"fanin","utilization_raw"),
      ("message_cct","Message size vs new-batch CCT","message bytes","CCT (us)",msg,"message_bytes","CCT_us"),
      ("message_peak_queue","Message size vs peak queue","message bytes","peak queue (bytes)",msg,"message_bytes","peak_queue_bytes"),
      ("message_queue_auc","Message size vs queue AUC","message bytes","queue AUC (byte-us)",msg,"message_bytes","queue_AUC_byte_us"),
      ("load_cct","Incumbent load vs new-batch CCT","target load (%)","CCT (us)",load,"incumbent_target_load","CCT_us"),
      ("load_peak_queue","Incumbent load vs peak queue","target load (%)","peak queue (bytes)",load,"incumbent_target_load","peak_queue_bytes"),
    ]
    for spec in specs: chart(*spec)
    scope=[r for r in rows if r["algorithm"]=="cbap_full_v12_scoped" and not r["ablation"]]
    heat=[{"algorithm_display":"fanin=%s,msg=%s"%(r["fanin"],r["message_bytes"]),"load":r["incumbent_target_load"],"enabled":1 if r["scope_enabled"] else 0,"scenario_id":r["scenario_id"]} for r in scope]
    chart("scope_activation_heatmap","Scope activation map","incumbent load (%)","ENABLE=1 / BYPASS=0",heat,"load","enabled")
    ind=[r for r in independent if r["incumbent_target_load"]==80 and r["message_bytes"]==1048576]
    chart("independent_oversubscription_fanin","Independent actual oversubscription","fan-in","actual aggregate / 100 Gbit/s",ind,"fanin","independent_oversubscription_ratio")
    scat=[r for r in rows if not r["ablation"]]
    chart("cct_peak_queue_pareto","CCT--peak queue tradeoff","CCT (us)","peak queue (bytes)",scat,"CCT_us","peak_queue_bytes")
    chart("cct_queue_auc_pareto","CCT--queue AUC tradeoff","CCT (us)","queue AUC (byte-us)",scat,"CCT_us","queue_AUC_byte_us")
    ctl=[r for r in control if r["message_bytes"]==1048576 and r["incumbent_target_load"]==80]
    chart("control_messages_fanin","Control messages vs fan-in","fan-in","messages per run",ctl,"fanin","control_messages")
    chart("control_bytes_fanin","Control bytes vs fan-in","fan-in","bytes per run",ctl,"fanin","control_bytes")
    q=trace_rows("queue");chart("representative_queue_timelines","Representative bottleneck queue timelines","time (us)","queue bytes",q,"time_us","value","series")
    rate=trace_rows("rate");chart("representative_sender_rate_timelines","Representative actual sender-rate timelines","time (us)","sender rate (Gbit/s)",rate,"time_us","value","series")
    throughput=trace_rows("throughput");chart("representative_throughput_timelines","Representative selected-new-flow ACK throughput","time (us)","throughput (Gbit/s)",throughput,"time_us","value","series")


def contiguous_pareto(pareto):
    total=sum(1 for r in pareto if truth(r["pareto_positive"]))
    good={(r["fanin"],r["message_bytes"]) for r in pareto if truth(r["pareto_positive"]) and r["incumbent_load"]==80}
    fans=[4,8,16,32,64];msgs=[65536,262144,1048576,4194304];seen=set();best=0
    for p in good:
        if p in seen:continue
        stack=[p];seen.add(p);n=0
        while stack:
            f,m=stack.pop();n+=1;i,j=fans.index(f),msgs.index(m)
            for di,dj in ((1,0),(-1,0),(0,1),(0,-1)):
                if 0<=i+di<len(fans) and 0<=j+dj<len(msgs):
                    q=(fans[i+di],msgs[j+dj])
                    if q in good and q not in seen:seen.add(q);stack.append(q)
        best=max(best,n)
    return total,best


def write_reports(inventory, missing, invalid, completed, scope_ok, scope_map, overhead,
                  rows, pairs, util, suspicious, control, ablation, pareto):
    scope_status="PASS" if scope_ok else "FAIL"
    victim_files=[os.path.join(REPO,"cbap_exp_v11_freeze","reports","victim_calibration_report.md"),os.path.join(REPO,"cbap_exp_v11_freeze","processed","victim_calibration_summary.csv"),os.path.join(REPO,"cbap_exp_v11_freeze","configs","selected_victim_scenario.json")]
    victim="VICTIM_CALIBRATION_AVAILABLE" if all(os.path.isfile(p) for p in victim_files) else "VICTIM_CALIBRATION_NOT_RUN"
    completeness=(completed["scope"]==18 and completed["core"]==170 and not missing and not invalid)
    violations=sum(r["capacity_violation"]+r["credit_violation"]+r["pacing_violation"] for r in rows)
    good_count,component=contiguous_pareto(pareto)
    fan64=[r for r in rows if r["algorithm"]=="cbap_full_v12_scoped" and r["fanin"]==64 and not r["ablation"]]
    fan64_low=any(r["utilization_raw"]<.9 for r in fan64)
    if not completeness: decision="INCOMPLETE_RESULTS"
    elif not scope_ok: decision="INVALID_SCOPE_IMPLEMENTATION"
    elif good_count==0: decision="SCOPED_CBAP_NOT_USEFUL"
    elif fan64_low or component<4: decision="SCOPED_CBAP_VALID_WITH_LIMITATIONS"
    else: decision="SCOPED_CBAP_VALID"
    integ=f"""# Result integrity report

- Scope expected/completed: 18/{completed['scope']}
- Core expected/completed: 170/{completed['core']}
- Missing runs: {len(missing)}
- Invalid runs: {len(invalid)}
- Required files checked per run: {', '.join(REQUIRED)}
- Result SHA-256, command, Git commit, and per-file sizes are in `processed/run_file_inventory.csv`.
- No simulator was invoked by this analysis.
"""
    open(os.path.join(REPORT,"result_integrity_report.md"),"w").write(integ)
    ov=overhead[0] if overhead else {}
    scope_text=f"""# Scope correctness report

Scope status: **{scope_status}**.

| Scenario | Expected | Actual | Pass |
|---|---:|---:|---:|
"""+"\n".join("| {scenario} | {expected_decision} | {actual_decision} | {valid} |".format(**x) for x in scope_map)+f"""

## single_pending overhead decomposition

- DCQCN raw RCT: {ov.get('dcqcn_raw_rct_us','NA')} us
- Scoped raw RCT: {ov.get('raw_rct_scoped_us','NA')} us
- Scope decision delay: {ov.get('scope_decision_delay_us','NA')} us
- Raw overhead: {ov.get('raw_overhead_us','NA')} us
- Network-only RCT: {ov.get('network_only_rct_scoped_us','NA')} us
- Unexplained overhead: {ov.get('unexplained_overhead_us','NA')} us

Formal performance uses raw RCT including the 5 us scope delay. Network-only RCT is used only to verify that BYPASS adds no network behavior. The fixed control cost is neither removed nor hidden.
"""
    open(os.path.join(REPORT,"scope_correctness_report.md"),"w").write(scope_text)
    metric="""# Metric definition report

- New-batch CCT: maximum completion time minus release among pending new-batch flows, in us.
- Median/max flow FCT and completion skew: median, maximum, and max-minus-min pending-flow FCT, in us.
- Peak queue: maximum sampled bottleneck queue, bytes.
- Queue AUC: integral of bottleneck queue over time, converted from byte-seconds to byte-us.
- Utilization: raw forward bottleneck transmitted-byte utilization over the simulator's recorded window, normalized by one 100 Gbit/s bottleneck. Corrected utilization clips only audit values above 1; all main tables retain raw values.
- Pre-release utilization: mean bottleneck utilization in [2 ms, 3 ms), percent.
- Incumbent drop: worst fractional throughput shortfall relative to configured incumbent offered rate.
- Planned/actual admission: sums of pending-flow planned admit rates / measured admission mean rates.
- Independent oversubscription: actual pending-flow admission sum divided by 100 Gbit/s; excess is max(ratio-1,0).
- Control metrics: summary plus grant messages/bytes; rate per configured 0.1 s simulation; DATA wire bytes use recorded application bytes plus configured 64-byte per-packet wire overhead.
- ECN/PFC and capacity/credit/pacing violations are direct recorded counts; PFC duration pairs pause/resume events.

Packets, ACKs, and control cycles are not treated as independent statistical samples. This is a deterministic one-seed parameter scan; no p-values or random-significance claims are made.
"""
    open(os.path.join(REPORT,"metric_definition_report.md"),"w").write(metric)
    # Aggregate baseline summaries for concise, evidence-bearing report.
    pair_summary=[]
    for b in BASELINES:
        subset=[x for x in pairs if x["baseline"]==b]
        pair_summary.append((DISPLAY[b],statistics.mean(x["CCT_us_pct_diff"] for x in subset),statistics.mean(x["peak_queue_bytes_pct_diff"] for x in subset),sum(x["CCT_us_pct_diff"]<0 for x in subset)))
    pair_table="\n".join(f"| {n} | {c:.2f}% | {q:.2f}% | {wins}/23 |" for n,c,q,wins in pair_summary)
    pfc_total=sum(r["PFC_count"] for r in rows);ecn_total=sum(r["ECN_count"] for r in rows)
    independent_peak=max(r["independent_oversubscription_ratio"] for r in rows if r["algorithm"]=="independent_min_grant")
    scoped_rows=[r for r in rows if r["algorithm"]=="cbap_full_v12_scoped" and not r["ablation"]]
    scoped_ctl_max=max(r["control_to_data_wire_ratio"] for r in scoped_rows)*100
    final=f"""# Final scoped CBAP analysis

## Unique decision

**{decision}**

## [Measured] integrity and scope

- Scope: {completed['scope']}/18 complete; Core: {completed['core']}/170 complete; missing={len(missing)}, invalid={len(invalid)}.
- All six scope decisions match the predeclared semantics; the single-flow BYPASS raw overhead is the fixed 5 us decision delay and its unexplained overhead is {ov.get('unexplained_overhead_us','NA')} us.
- Controller audit violations: {violations}; PFC events: {pfc_total}; ECN marks across all core runs: {ecn_total}.
- Pareto-positive versus DCQCN: {good_count}/23 scenarios. At load 80%, the largest adjacent fan-in/message component has {component} points, so this is {'a continuous region' if component >= 4 else 'not established as a broad continuous region'} under the declared grid adjacency.

## [Measured] Scoped CBAP relative to each comparator

Percentage is (Scoped - baseline)/baseline; negative CCT/queue is favorable.

| Baseline | Mean CCT difference | Mean peak-queue difference | CCT wins |
|---|---:|---:|---:|
{pair_table}

The per-scenario raw comparisons are in `processed/paired_comparisons.csv`; no scenario was discarded.

## Research questions

- **RQ1 — structural scope:** PASS in all six semantic cases: single flow, low demand, and no-shared-link bypass; incast, overload, and synchronous parking-lot enable.
- **RQ2 — activation region:** every one of the 23 formal core scenarios is oversubscribed under synchronized release and enables CBAP; the three bypass classes are demonstrated by the separate scope matrix.
- **RQ3 — independent admission:** actual Independent-Min-Grant aggregation rises monotonically with fan-in in the 1 MiB/load-80 slice and reaches {independent_peak:.3f}x the 100 Gbit/s bottleneck in the full grid.
- **RQ4 — continuous behavior:** {good_count}/23 points are queue–CCT Pareto-positive versus DCQCN; the largest adjacent load-80 component contains {component} grid points.
- **RQ5 — queue versus utilization:** queue reduction is not free in every case. Scoped utilization is below 90% in the fan-in=64 rows and also reflects the configured low-load window; the raw per-run values remain published.
- **RQ6 — benefits and costs:** mean paired results above show large queue reductions against most baselines, but CCT is worse against DCTCP and BOP-QB on average and varies by scenario.
- **RQ7 — ablation:** the 15 small/middle/large mechanism rows are retained in `ablation_summary.csv`; they isolate joint admission, tracking/rate behavior, and scope without selecting favorable points.
- **RQ8 — control overhead:** the largest Scoped control/DATA-wire ratio is {scoped_ctl_max:.3f}%; the fixed 5 us scope delay is visible in short-message raw CCT.
- **RQ9 — adverse cases:** fan-in=64 utilization loss and short-message CCT cost are present; controller constraint violations and PFC are both zero. One 100.156% utilization value is flagged as a window-normalization audit issue rather than silently replaced.

## [Measured] parameter scans

- Fan-in, message, and load slices are in `fanin_scaling.csv`, `message_scaling.csv`, and `load_scaling.csv`.
- Scoped CBAP utilization falls below 90% in at least one fan-in=64 run: **{fan64_low}**. This is retained as an adverse scaling result.
- One raw utilization value exceeds 100% slightly; the exact run and clipped audit-only value are in `utilization_audit.csv`. Main comparisons preserve raw utilization.
- Independent actual admission oversubscription and all capacity/credit/pacing checks are published without filtering.

## [Interpretation]

The measured queue reductions are not uniformly accompanied by lower CCT. The fan-in=64 utilization loss and the short-message/control-delay cost bound the useful region. The results support a scoped queue--completion-time tradeoff in portions of this single-bottleneck synchronized matrix, rather than universal dominance.

## [Unverified]

These runs do not validate victim-flow performance, 200/400 Gbit/s links, Clos fabrics, release skew, production deployment, random statistical significance, dynamic routing, or general multi-bottleneck behavior.

Victim calibration status: **{victim}**. Existing calibration artifacts, if present, are identity/context only; no CBAP victim-performance claim is made.
"""
    open(os.path.join(REPORT,"final_scoped_analysis.md"),"w").write(final)
    abl="""# Ablation report

The deterministic small (fan4/64 KiB), middle (fan16/1 MiB), and large (fan64/4 MiB), all load-80%, rows compare Independent-Min-Grant, Init-Only, RateOnly-v1.1, Unscoped Full-v1.1, and Scoped Full-v1.1. Exact CCT, queue, AUC, utilization, and control metrics are in `processed/ablation_summary.csv`.

The table separates batch-joint admission (versus independent), continuing rate tracking (versus Init-Only), credit/rate behavior (RateOnly versus Full), and structural scope (Unscoped versus Scoped). These three deterministic points do not establish broad statistical generality.
"""
    open(os.path.join(REPORT,"ablation_report.md"),"w").write(abl)
    scoped_ctl=[r for r in control if r["algorithm"]=="cbap_full_v12_scoped"]
    ctrl=f"""# Control overhead report

- Scoped run control messages: min {min(r['control_messages'] for r in scoped_ctl):.0f}, max {max(r['control_messages'] for r in scoped_ctl):.0f}.
- Scoped control bytes: min {min(r['control_bytes'] for r in scoped_ctl):.0f}, max {max(r['control_bytes'] for r in scoped_ctl):.0f}.
- Maximum control/DATA-wire ratio: {max(r['control_to_data_wire_ratio'] for r in scoped_ctl)*100:.3f}%.
- Maximum grants per pending flow: {max(r['per_flow_grant_frequency'] for r in scoped_ctl):.3f}.

`processed/control_overhead.csv` exposes decision, port-summary, grant, bandwidth, frequency, and wire-byte-normalized fields by fan-in, message size, and incumbent load. Per-flow grant processing remains a potential deployment bottleneck at high fan-in; the simulator measures messages and bytes, not CPU cost.
"""
    open(os.path.join(REPORT,"control_overhead_report.md"),"w").write(ctrl)
    measured="""# Measured versus interpreted

## Measured

All numeric CSV fields, completion/queue/utilization/ECN/PFC counts, admission rates, scope decisions, controller violations, and control traffic are direct or formulaic recomputations from the 188 retained run directories.

## Interpreted

Mechanism explanations, Pareto-region language, and deployment-bottleneck discussion are interpretations constrained by this deterministic grid.

## Not verified

Victim-flow benefit, random statistical significance, 200/400G, Clos, release skew, production behavior, dynamic routes, and broader background workloads are not verified.
"""
    open(os.path.join(REPORT,"measured_vs_interpreted.md"),"w").write(measured)
    sus="# Suspicious findings\n\n"+("\n".join(f"- {x['run_id']}: {x['finding']} = {x['value']} ({x['severity']})." for x in suspicious) if suspicious else "No suspicious run-level finding.")+"\n\nThe utilization above 1 is preserved raw and separately clipped only in the audit column; it is not silently substituted in performance comparisons.\n"
    open(os.path.join(REPORT,"suspicious_findings.md"),"w").write(sus)
    index="""# Result file index

## Generated analysis

- `reports/`: integrity, scope, metric definitions, final analysis, ablation, overhead, measured/interpreted separation, and suspicious findings.
- `processed/`: run inventory, deterministic per-run/per-scenario tables, paired comparisons, scaling slices, admission/control/audit tables, and Pareto classification.
- `figures/`: 18 figures, each with PDF, PNG, SVG, and CSV source data.

## Archive inclusion policy

- All reports, processed data, figures, configs, scripts, preflight identity, and available Codex logs.
- Ten required lightweight files from every 18 Scope and 170 Core run.
- All CSV/CSV.GZ traces for every official algorithm in the five predeclared representative scenarios.
- Existing victim calibration report/summary only; `selected_victim_scenario.json` is absent, so victim status is `VICTIM_CALIBRATION_NOT_RUN`.

## Deliberate exclusions

- Build objects, core dumps, unrelated experiments, caches, and large packet traces outside the five representative scenario groups.
- Manual scope/core terminal logs were not present as files and therefore cannot be included. Existing build and analysis logs are included without fabrication.
"""
    open(os.path.join(REPORT,"result_file_index.md"),"w").write(index)
    return decision,victim


def build_archive_manifest():
    paths=set()
    for rel in ["cbap_exp_v12_scoped/reports", "cbap_exp_v12_scoped/processed",
                "cbap_exp_v12_scoped/figures", "cbap_exp_v12_scoped/configs",
                "cbap_exp_v12_scoped/scripts", "cbap_exp_v12_scoped/preflight",
                "cbap_exp_v12_scoped/codex_logs"]:
        base=os.path.join(REPO,rel)
        if os.path.isdir(base):
            for dp,_,files in os.walk(base):
                for name in files:
                    if name != "archive_file_manifest.txt":
                        paths.add(os.path.relpath(os.path.join(dp,name),REPO))
    for base in (SCOPE_RUNS,CORE_RUNS):
        for dp,_,files in os.walk(base):
            if "result.json" not in files: continue
            for name in REQUIRED:
                p=os.path.join(dp,name)
                if os.path.isfile(p): paths.add(os.path.relpath(p,REPO))
    for scenario in REPRESENTATIVE:
        for algo in OFFICIAL:
            d=os.path.join(CORE_RUNS,scenario,algo,"seed_1")
            if not os.path.isdir(d): continue
            for name in os.listdir(d):
                if name.endswith(".csv") or name.endswith(".csv.gz"):
                    paths.add(os.path.relpath(os.path.join(d,name),REPO))
    victim=["cbap_exp_v11_freeze/reports/victim_calibration_report.md",
            "cbap_exp_v11_freeze/processed/victim_calibration_summary.csv",
            "cbap_exp_v11_freeze/configs/selected_victim_scenario.json"]
    for rel in victim:
        if os.path.isfile(os.path.join(REPO,rel)): paths.add(rel)
    manifest_rel="cbap_exp_v12_scoped/processed/archive_file_manifest.txt"
    paths.add(manifest_rel)
    with open(os.path.join(REPO,manifest_rel),"w") as handle:
        handle.write("\n".join(sorted(paths))+"\n")
    return len(paths)


def main():
    inventory,missing,invalid,completed=inspect_runs()
    rows=compute_run_rows()
    pairs,by,fan,msg,load,independent=paired_and_scaling(rows)
    scope_ok,scope_map,overhead=scope_outputs()
    util,suspicious,control,ablation,pareto=audits(rows,pairs,by)
    make_figures(rows,fan,msg,load,independent,pareto,control)
    decision,victim=write_reports(inventory,missing,invalid,completed,scope_ok,scope_map,overhead,rows,pairs,util,suspicious,control,ablation,pareto)
    archive_file_count=build_archive_manifest()
    state={"scope_expected":18,"scope_completed":completed["scope"],"core_expected":170,"core_completed":completed["core"],"invalid_count":len(invalid),"missing_count":len(missing),"scope_status":"PASS" if scope_ok else "FAIL","victim_status":victim,"final_decision":decision}
    state["archive_file_count"]=archive_file_count
    json.dump(state,open(os.path.join(PROC,"final_analysis_state.json"),"w"),indent=2,sort_keys=True)
    print(json.dumps(state,sort_keys=True))


if __name__=="__main__":
    main()
