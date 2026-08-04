#!/usr/bin/env python3
import csv
import json
import os
import subprocess
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def write_csv(path, fields, rows):
    with open(path, "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class CollectiveCompletionScope(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.run = self.temp.name
        with open(os.path.join(self.run, "run_meta.json"), "w") as stream:
            json.dump({"scenario": "synthetic", "algorithm": "dcqcn",
                       "seed": 1, "cc_mode": 1, "exit_status": 0,
                       "log_truncated": False}, stream)
        with open(os.path.join(self.run, "manifest.json"), "w") as stream:
            json.dump({}, stream)
        with open(os.path.join(self.run, "scenario_meta.json"), "w") as stream:
            json.dump({"scenario": "synthetic", "pending_count": 1,
                       "pending_flow_ids": [1],
                       "incumbent_flow_ids": [0]}, stream)
        with open(os.path.join(self.run, "rounds.txt"), "w") as stream:
            stream.write("flow_id round_id group_id participant_count "
                         "round_bytes a b c release_time_ns\n")
            stream.write("0 0 0 1 100 0 0 0 1000\n")
            stream.write("1 0 1 1 100 0 0 0 2000\n")
        write_csv(os.path.join(self.run, "flow_summary.csv"),
                  ["flow_id", "finish_time", "start_time", "acked_bytes",
                   "completed"],
                  [{"flow_id": 1, "finish_time": 0.000010,
                    "start_time": 0.000002, "acked_bytes": 100,
                    "completed": 1}])
        write_csv(os.path.join(self.run, "round_summary.csv"),
                  ["flow_id", "round_group_id", "ack_completion_time"],
                  [{"flow_id": 0, "round_group_id": 0,
                    "ack_completion_time": 0},
                   {"flow_id": 1, "round_group_id": 1,
                    "ack_completion_time": 0.000010}])
        write_csv(os.path.join(self.run, "group_round_summary.csv"),
                  ["group_id"], [{"group_id": 1}])
        write_csv(os.path.join(self.run, "selected_link_timeseries.csv"),
                  ["queue_bytes", "utilization", "ecn_marks_delta"],
                  [{"queue_bytes": 10, "utilization": 0.5,
                    "ecn_marks_delta": 0}])
        write_csv(os.path.join(self.run, "pfc_events.csv"), ["time"], [])
        write_csv(os.path.join(self.run, "cbap_flow_state.csv"),
                  ["capacity_violations", "credit_violations"],
                  [{"capacity_violations": 0, "credit_violations": 0}])

    def tearDown(self):
        self.temp.cleanup()

    def test_incomplete_incumbent_does_not_invalidate_collective(self):
        checked = subprocess.run(
            ["python3", os.path.join(ROOT, "scripts", "check_outputs.py"),
             "--allow-no-complete-flag", self.run],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.assertEqual(checked.returncode, 0, checked.stdout)
        subprocess.check_call(
            ["python3", os.path.join(ROOT, "scripts",
                                     "collect_run_metrics.py"), self.run])
        with open(os.path.join(self.run, "result.json")) as stream:
            result = json.load(stream)
        self.assertTrue(result["all_pending_flows_completed"])
        self.assertEqual(result["metric_scope"], "pending_collective_only")
        self.assertEqual(result["completed_incumbent_flow_count"], 0)
        self.assertAlmostEqual(result["group_rct_max_us"], 8.0)

    def test_missing_pending_flow_is_rejected(self):
        os.replace(os.path.join(self.run, "flow_summary.csv"),
                   os.path.join(self.run, "flow_summary.saved"))
        write_csv(os.path.join(self.run, "flow_summary.csv"),
                  ["flow_id", "finish_time", "start_time", "acked_bytes",
                   "completed"], [])
        checked = subprocess.run(
            ["python3", os.path.join(ROOT, "scripts", "check_outputs.py"),
             "--allow-no-complete-flag", self.run],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.assertNotEqual(checked.returncode, 0)
        self.assertIn("missing completed pending flows", checked.stdout)


if __name__ == "__main__":
    unittest.main()
