#!/usr/bin/env python3
import argparse
import csv
import json
import math
import os
import statistics
from mainlib import percentile

NA = "NA"


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def number(row, key, default=0.0):
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def write_csv(path, fields, values):
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        if isinstance(values, dict):
            writer.writerow(values)
        else:
            writer.writerows(values)


def jain(values):
    if not values or not any(values):
        return NA
    return sum(values) ** 2 / (len(values) * sum(x * x for x in values))


def aggregate(run_dir):
    with open(os.path.join(run_dir, "run_meta.json")) as handle:
        meta = json.load(handle)
    flows = read_csv(os.path.join(run_dir, "flow_summary.csv"))
    rounds = read_csv(os.path.join(run_dir, "round_summary.csv"))
    groups = read_csv(os.path.join(run_dir, "group_round_summary.csv"))
    links = read_csv(os.path.join(run_dir, "selected_link_timeseries.csv"))
    wire = read_csv(os.path.join(run_dir, "raw_wire_size_summary.csv"))
    feedback = read_csv(os.path.join(run_dir, "feedback_summary.csv"))
    controller = read_csv(os.path.join(run_dir, "controller_summary.csv"))
    pfc = read_csv(os.path.join(run_dir, "pfc_events.csv"))
    plans = read_csv(os.path.join(run_dir, "flow_plan.csv"))
    decisions = read_csv(os.path.join(run_dir, "bop_qb_group_decisions.csv"))

    qvals = [number(x, "queue_bytes") for x in links]
    sample_us = 10.0
    ecn_threshold = 400000.0
    queue_fields = [
        "queue_mean_bytes", "queue_p95_bytes", "queue_p99_bytes",
        "queue_max_bytes", "queue_round_max_mean_bytes",
        "time_above_ecn_threshold_us", "time_above_pfc_threshold_us"]
    qround = [number(x, "group_queue_max_bytes") for x in groups]
    queue_row = {
        "queue_mean_bytes": statistics.mean(qvals) if qvals else NA,
        "queue_p95_bytes": percentile(qvals, .95) if qvals else NA,
        "queue_p99_bytes": percentile(qvals, .99) if qvals else NA,
        "queue_max_bytes": max(qvals) if qvals else NA,
        "queue_round_max_mean_bytes": statistics.mean(qround) if qround else NA,
        "time_above_ecn_threshold_us":
            sum(q >= ecn_threshold for q in qvals) * sample_us,
        "time_above_pfc_threshold_us":
            sum(number(x, "pfc_paused") > 0 for x in links) * sample_us,
    }
    write_csv(os.path.join(run_dir, "queue_summary.csv"),
              queue_fields, queue_row)

    packets = sum(int(number(x, "packet_count")) for x in wire)
    ecn = sum(int(number(x, "ecn_marks_delta")) for x in links)
    if not ecn:
        ecn = sum(int(number(x, "group_ecn_marks")) for x in groups)
    congestion_fields = [
        "ecn_marks", "ecn_marks_per_1000_data_packets", "pfc_events",
        "pfc_pause_duration_us", "dropped_packets", "retransmitted_packets"]
    pause_starts = {}
    pause_ns = 0
    pfc_start_count = 0
    for row in sorted(pfc, key=lambda x: int(x["time_ns"])):
        key = (row["node_id"], row["if_index"], row["q_index"])
        event = int(row["event_type"])
        when = int(row["time_ns"])
        if event and key not in pause_starts:
            pause_starts[key] = when
            pfc_start_count += 1
        elif not event and key in pause_starts:
            pause_ns += max(when - pause_starts.pop(key), 0)
    simulation_end_ns = max(
        [int(number(x, "barrier_completion_time") * 1e9)
         for x in groups] or [0])
    for when in pause_starts.values():
        pause_ns += max(simulation_end_ns - when, 0)
    congestion_row = {
        "ecn_marks": ecn,
        "ecn_marks_per_1000_data_packets":
            (1000.0 * ecn / packets if packets else NA),
        "pfc_events": pfc_start_count,
        "pfc_pause_duration_us": pause_ns / 1000.0,
        "dropped_packets": NA,
        "retransmitted_packets": NA,
    }
    write_csv(os.path.join(run_dir, "congestion_summary.csv"),
              congestion_fields, congestion_row)

    payload = sum(int(number(x, "application_payload_bytes")) for x in wire)
    total_wire = sum(number(x, "mean_wire_data_bytes") *
                     int(number(x, "packet_count")) for x in wire)
    wmeans = [number(x, "mean_wire_data_bytes") for x in wire]
    wmins = [number(x, "min_wire_data_bytes") for x in wire]
    wmaxs = [number(x, "max_wire_data_bytes") for x in wire]
    int_bytes = packets * 42 if meta["algorithm"] in (
        "hpcc_int", "bop_qb", "crfm_gate", "bop") else 0
    wire_fields = [
        "application_payload_bytes", "total_wire_data_bytes",
        "mean_wire_data_bytes", "min_wire_data_bytes",
        "max_wire_data_bytes", "ACK_bytes", "CNP_bytes", "INT_bytes",
        "total_control_bytes", "data_packet_count"]
    wire_row = {
        "application_payload_bytes": payload,
        "total_wire_data_bytes": int(round(total_wire)),
        "mean_wire_data_bytes": statistics.mean(wmeans) if wmeans else NA,
        "min_wire_data_bytes": min(wmins) if wmins else NA,
        "max_wire_data_bytes": max(wmaxs) if wmaxs else NA,
        "ACK_bytes": NA, "CNP_bytes": NA, "INT_bytes": int_bytes,
        "total_control_bytes": NA, "data_packet_count": packets,
    }
    write_csv(os.path.join(run_dir, "wire_summary.csv"),
              wire_fields, wire_row)

    group_rct = [number(x, "group_rct") * 1e6 for x in groups]
    flow_fct = [number(x, "round_completion_time") * 1e6 for x in rounds]
    active = sum(number(x, "group_rct") for x in groups)
    lower = [8.0 * number(x, "total_round_bytes") / 1e11 * 1e6
             for x in groups]
    completions_by_round = {}
    rcts_by_round = {}
    for row in rounds:
        completions_by_round.setdefault(row["round_id"], []).append(
            number(row, "ack_completion_time"))
        rcts_by_round.setdefault(row["round_id"], []).append(
            number(row, "round_completion_time"))
    skews, p75_tails, p90_tails, fairness = [], [], [], []
    for round_id, values in completions_by_round.items():
        barrier = max(values)
        skews.append((barrier - min(values)) * 1e6)
        p75_tails.append((barrier - percentile(values, .75)) * 1e6)
        p90_tails.append((barrier - percentile(values, .90)) * 1e6)
        rcts = rcts_by_round.get(round_id, [])
        if rcts and all(value > 0 for value in rcts):
            fairness.append(jain([1.0 / value for value in rcts]))
    rate_updates = sum(int(number(x, "direct_hpcc_updates")) for x in controller)
    feedback_count = sum(int(number(x, "total_feedback")) for x in feedback)
    is_bop = meta["algorithm"] in ("bop", "bop_qb")
    credits = [number(x, "group_credit_bytes") for x in decisions]
    totals = [number(x, "total_round_bytes") for x in decisions]
    base_by_group = {}
    phase = []
    for row in plans:
        key = (row.get("group_id"), row.get("round_id"))
        base_by_group[key] = base_by_group.get(key, 0.0) + number(
            row, "qb_base_rate_bps" if meta["algorithm"] == "bop_qb"
            else "selected_rate_bps")
        phase.append(number(row, "phase_offset_ns"))
    base_sums = list(base_by_group.values())
    summary_fields = [
        "scenario", "algorithm", "seed", "group_rct_mean_us",
        "group_rct_p50_us", "group_rct_p95_us", "group_rct_p99_us",
        "group_rct_max_us", "theoretical_lower_bound_us",
        "lower_bound_efficiency", "payload_goodput_gbps",
        "wire_throughput_gbps", "active_payload_utilization",
        "active_wire_utilization", "flow_fct_mean_us", "flow_fct_p50_us",
        "flow_fct_p95_us", "flow_fct_p99_us", "flow_fct_max_us",
        "completion_skew_us", "barrier_minus_p75_us",
        "barrier_minus_p90_us", "jain_completion_fairness",
        "rate_update_count", "feedback_message_count", "T_star_us",
        "group_credit_bytes", "group_credit_fraction",
        "base_rate_sum_gbps", "max_capacity_violation_bps",
        "phase_span_us", "group_decision_count", "safety_formula_valid"]
    total_payload = sum(number(x, "total_round_bytes") for x in groups)
    mean_lower = statistics.mean(lower) if lower else NA
    mean_rct = statistics.mean(group_rct) if group_rct else NA
    summary = {
        "scenario": meta["scenario"], "algorithm": meta["algorithm"],
        "seed": meta["seed"],
        "group_rct_mean_us": mean_rct,
        "group_rct_p50_us": percentile(group_rct, .50),
        "group_rct_p95_us": percentile(group_rct, .95),
        "group_rct_p99_us": percentile(group_rct, .99),
        "group_rct_max_us": max(group_rct) if group_rct else NA,
        "theoretical_lower_bound_us": mean_lower,
        "lower_bound_efficiency":
            (mean_lower / mean_rct if group_rct and mean_rct else NA),
        "payload_goodput_gbps": total_payload * 8 / active / 1e9
            if active else NA,
        "wire_throughput_gbps": total_wire * 8 / active / 1e9
            if active else NA,
        "active_payload_utilization": total_payload * 8 / active / 1e11
            if active else NA,
        "active_wire_utilization": total_wire * 8 / active / 1e11
            if active else NA,
        "flow_fct_mean_us": statistics.mean(flow_fct) if flow_fct else NA,
        "flow_fct_p50_us": percentile(flow_fct, .50),
        "flow_fct_p95_us": percentile(flow_fct, .95),
        "flow_fct_p99_us": percentile(flow_fct, .99),
        "flow_fct_max_us": max(flow_fct) if flow_fct else NA,
        "completion_skew_us": statistics.mean(skews) if skews else NA,
        "barrier_minus_p75_us": statistics.mean(p75_tails)
            if p75_tails else NA,
        "barrier_minus_p90_us": statistics.mean(p90_tails)
            if p90_tails else NA,
        "jain_completion_fairness": statistics.mean(fairness)
            if fairness else NA,
        "rate_update_count": rate_updates,
        "feedback_message_count": feedback_count,
        "T_star_us": statistics.mean(
            [number(x, "T_star") * 1e6 for x in groups]) if is_bop else NA,
        "group_credit_bytes": statistics.mean(credits)
            if credits else (0 if meta["algorithm"] == "bop" else NA),
        "group_credit_fraction": statistics.mean(
            [c / t for c, t in zip(credits, totals) if t])
            if credits else (0 if meta["algorithm"] == "bop" else NA),
        "base_rate_sum_gbps": statistics.mean(base_sums) / 1e9
            if is_bop and base_sums else NA,
        "max_capacity_violation_bps": max(
            [max(x - 1e11, 0) for x in base_sums] or [0])
            if is_bop else NA,
        "phase_span_us": (max(phase) - min(phase)) / 1000
            if is_bop and phase else NA,
        "group_decision_count": len(groups) if is_bop else NA,
        "safety_formula_valid": (
            int(all(x.get("safety_bound_valid") == "1" for x in decisions))
            if decisions else (1 if meta["algorithm"] == "bop" else NA)),
    }
    write_csv(os.path.join(run_dir, "algorithm_summary.csv"),
              summary_fields, summary)

    if is_bop:
        if decisions:
            with open(os.path.join(run_dir, "bop_group_decisions.csv"),
                      "w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=decisions[0].keys())
                writer.writeheader()
                writer.writerows(decisions)
        else:
            fields = ["group_id", "round_id", "T_star_us",
                      "group_credit_bytes", "safety_formula_valid"]
            derived = [{"group_id": x["group_id"], "round_id": x["round_id"],
                        "T_star_us": number(x, "T_star") * 1e6,
                        "group_credit_bytes": 0,
                        "safety_formula_valid": 1} for x in groups]
            write_csv(os.path.join(run_dir, "bop_group_decisions.csv"),
                      fields, derived)
        if plans:
            fields = list(plans[0].keys())
            write_csv(os.path.join(run_dir, "bop_flow_rates.csv"),
                      fields, plans)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    aggregate(os.path.abspath(parser.parse_args().run_dir))


if __name__ == "__main__":
    main()
