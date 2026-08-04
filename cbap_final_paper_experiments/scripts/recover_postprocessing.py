#!/usr/bin/env python3
"""Recover metrics for a completed ns-3 run without rerunning simulation."""
import argparse
import csv
import gzip
import json
import os
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(ROOT, ".."))


def rows(path):
    if not os.path.isfile(path): return []
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", newline="") as stream: return list(csv.DictReader(stream))


def locate(run, name):
    plain = os.path.join(run, name)
    compressed = plain + ".gz"
    return plain if os.path.isfile(plain) else compressed if os.path.isfile(compressed) else None


def compress_detailed_outputs(run):
    if os.environ.get("KEEP_RAW", "0") == "1": return
    for name in ("selected_link_timeseries.csv", "selected_flow_timeseries.csv",
                 "cbap_packet_trace.csv", "sender_tx_trace.csv",
                 "cbap_port_summary.csv", "applied_rate_audit.csv"):
        source = os.path.join(run, name)
        if not os.path.isfile(source): continue
        destination = source + ".gz"
        with open(source, "rb") as incoming, gzip.open(destination, "wb") as outgoing:
            for block in iter(lambda: incoming.read(1 << 20), b""):
                outgoing.write(block)
        os.unlink(source)


def atomic_json(path, value):
    temporary = path + ".recovery.tmp"
    with open(temporary, "w") as stream:
        json.dump(value, stream, indent=2, sort_keys=True); stream.write("\n")
    os.replace(temporary, path)


def raw_complete(run):
    if os.path.isfile(os.path.join(run, "interrupted.flag")):
        return False, "explicitly_interrupted"
    flow_file = os.path.join(run, "flow.txt")
    if not os.path.isfile(flow_file): return False, "missing_flow_input"
    planned = sum(1 for line in open(flow_file) if line.split()) - 1
    flow = rows(os.path.join(run, "flow_summary.csv"))
    rounds = rows(os.path.join(run, "round_summary.csv"))
    if planned <= 0 or len(rounds) < planned:
        return False, "raw_count_mismatch"
    scenario_path = os.path.join(run, "scenario_meta.json")
    if not os.path.isfile(scenario_path): return False, "missing_scenario_meta"
    scenario = json.load(open(scenario_path))
    newcomers = set(int(x) for x in scenario.get("pending_flow_ids", []))
    flow_by_id = {int(float(row["flow_id"])): row for row in flow}
    round_by_id = {}
    for row in rounds: round_by_id.setdefault(int(float(row["flow_id"])), []).append(row)
    if not newcomers or any(fid not in flow_by_id for fid in newcomers):
        return False, "missing_newcomer_summary"
    if any(str(flow_by_id[fid].get("completed", "0")).lower() not in
           ("1", "true") for fid in newcomers):
        return False, "unfinished_newcomer"
    if any(not round_by_id.get(fid) or any(float(row.get(
            "ack_completion_time", 0) or 0) <= 0 for row in round_by_id[fid])
           for fid in newcomers):
        return False, "unfinished_newcomer_round"
    if locate(run, "selected_link_timeseries.csv") is None:
        return False, "missing_link_timeseries"
    return True, "complete_raw_outputs"


def ensure_headers(run):
    headers = {
        "scope_summary.csv": "batch_id,application_ready_ns,decision_complete_ns,decision_delay_ns,flow_count,used_link_count,enabled,reason,triggering_link_count,maximum_pending_count,maximum_oversubscription_ratio",
        "scope_link_summary.csv": "batch_id,application_ready_ns,newest_summary_sample_ns,newest_summary_delivery_ns,link_id,switch_id,egress_port,pending_count,A_admit_bps,independent_aggregate_bps,oversubscription_bps,oversubscription_ratio,enabled_on_link,pre_release_causal",
        "applied_rate_audit.csv": "link_id,epoch,C_l,rho_C_l,C_effective_l,planner_grant_sum_bps,target_rate_sum_bps,applied_rate_sum_bps,actual_tx_rate_sum_bps,background_rate_bps,legacy_floor_rate_bps,flows_below_legacy_floor,floor_clamp_count,rate_clamp_delta_sum_bps,zero_grant_flow_count,paused_zero_grant_count,applied_capacity_excess_bps,applied_capacity_violation,actual_arrival_excess_bps",
        "sender_tx_trace.csv": "time_ns,event,flow_id,batch_id,packet_seq,wire_bytes,phase,current_rate_bps,target_rate_bps,admit_rate_bps,base_rate_bps,credit_gate_active,credit_remaining_bytes,scheduled_time_ns,actual_send_time_ns,previous_tx_time_ns,expected_gap_ns,actual_gap_ns,reschedule_reason",
    }
    for name, header in headers.items():
        path = os.path.join(run, name)
        if (not os.path.isfile(path) or os.path.getsize(path) == 0) and \
                not os.path.isfile(path + ".gz"):
            with open(path, "w") as stream: stream.write(header + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir"); parser.add_argument("--probe", action="store_true")
    args = parser.parse_args(); run = os.path.abspath(args.run_dir)
    complete, reason = raw_complete(run)
    if not complete:
        if not args.probe: print("NOT_RECOVERABLE " + reason, file=sys.stderr)
        return 2
    meta_path = os.path.join(run, "run_meta.json")
    meta = json.load(open(meta_path))
    scenario = meta.get("scenario_id", meta.get("scenario"))
    if not scenario: return 2
    meta.update({"scenario": scenario, "subcase": scenario,
                 "exit_status": 0, "status": "finished",
                 "postprocessing_recovered": True,
                 "postprocessing_recovery_time_unix": time.time()})
    atomic_json(meta_path, meta)
    with open(os.path.join(run, "exit_status.txt"), "w") as stream: stream.write("0\n")
    full_log = os.path.join(run, "stdout.full.log")
    short_log = os.path.join(run, "stdout.log")
    if not os.path.isfile(short_log) and os.path.isfile(full_log):
        with open(full_log, "rb") as stream:
            stream.seek(max(0, os.path.getsize(full_log) - 10485760))
            data = stream.read()
        with open(short_log, "wb") as stream: stream.write(data)
    ensure_headers(run)
    commands = [
        ["python3", os.path.join(REPO, "cbap_exp", "scripts", "collect_run_metrics.py"), run],
        ["python3", os.path.join(REPO, "cbap_exp", "scripts", "materialize_required_summaries.py"), run],
        ["python3", os.path.join(ROOT, "scripts", "materialize_incumbent_summary.py"), run],
    ]
    for command in commands: subprocess.check_call(command)
    compress_detailed_outputs(run)
    commands = [
        ["python3", os.path.join(REPO, "cbap_final_metric_pipeline", "scripts",
                                 "collect_full_work_metrics.py"), "--run-dir", run,
                                 "--output-dir", run],
        ["python3", os.path.join(ROOT, "scripts", "check_outputs.py"),
         "--pre-complete", run],
    ]
    for command in commands: subprocess.check_call(command)
    open(os.path.join(run, "completed.flag"), "a").close()
    print("POSTPROCESS_RECOVERED " + os.path.basename(run))
    return 0


if __name__ == "__main__": sys.exit(main())
