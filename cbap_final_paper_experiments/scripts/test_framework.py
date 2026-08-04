#!/usr/bin/env python3
import csv
import json
import os
import subprocess
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class FrameworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "manifests", "all_runs.csv")) as stream:
            cls.rows = list(csv.DictReader(stream))

    def test_total(self): self.assertEqual(len(self.rows), 1408)
    def test_family_counts(self):
        counts = {}
        for row in self.rows: counts[row["experiment_family"]] = counts.get(row["experiment_family"], 0) + 1
        self.assertEqual(counts, {"single_bottleneck": 560, "release_skew": 420,
            "multibottleneck": 56, "clos": 140, "randomized": 210,
            "ablation": 22})
    def test_frozen_identity(self):
        rows = [r for r in self.rows if r["algorithm"] == "cbap_full_v13_ratefloor_fix"]
        self.assertTrue(rows); self.assertTrue(all(r["cc_mode"] == "25" for r in rows))
        self.assertTrue(all(r["rate_floor_policy"] == "1" for r in rows))
    def test_bop_identity(self):
        self.assertTrue(all(r["cc_mode"] == "15" for r in self.rows if r["algorithm"] == "bop_qb"))
    def test_clos_count(self):
        clos = [r for r in self.rows if r["experiment_family"] == "clos"]
        self.assertEqual(len(set(r["scenario_id"] for r in clos)), 20)
    def test_random_seed_changes_inputs(self):
        rows = [r for r in self.rows if r["experiment_family"] == "randomized" and r["algorithm"] == "dcqcn"]
        self.assertEqual(len(rows), 30)
        self.assertEqual(len(set(r["random_input_hash"] for r in rows)), 30)
    def test_static_auditor(self):
        subprocess.check_call(["python3", os.path.join(ROOT, "scripts", "audit_framework.py")])
    def test_seed1_bounded_trace_contract(self):
        manifest = os.path.join(ROOT, "manifests", "preflight.csv")
        with open(manifest) as stream: rows = list(csv.DictReader(stream))
        with tempfile.TemporaryDirectory() as temporary:
            for row in rows:
                run = os.path.join(temporary, row["algorithm"])
                subprocess.check_call(["python3", os.path.join(ROOT, "scripts", "prepare_run.py"),
                                       manifest, row["run_id"], run])
                config = {}
                with open(os.path.join(run, "config.txt")) as stream:
                    for line in stream:
                        words = line.split()
                        if words: config[words[0]] = " ".join(words[1:])
                self.assertTrue(config["CBAP_PACKET_TRACE_FILE"])
                self.assertEqual(config["CBAP_PACKET_TRACE_FILE"], "/dev/null")
                self.assertGreater(int(config["CBAP_PACKET_TRACE_MAX_MB"]), 0)
                self.assertLessEqual(int(config["CBAP_PACKET_TRACE_MAX_MB"]), 256)
    def test_cbap_idle_stop_requires_all_configured_flows(self):
        source = os.path.join(ROOT, "..", "simulation", "src",
                              "point-to-point", "model", "rdma-hw.cc")
        with open(source) as stream:
            text = stream.read()
        self.assertIn("s_cbapFlows.size() == s_cbapFlowPaths.size()", text)
        self.assertIn("allConfiguredFlowsFinished", text)
        self.assertIn("s_cbapStarted = false", text)
    def test_interrupted_run_is_not_recovered(self):
        with tempfile.TemporaryDirectory() as temporary:
            open(os.path.join(temporary, "interrupted.flag"), "w").close()
            result = subprocess.run([
                "python3", os.path.join(ROOT, "scripts",
                "recover_postprocessing.py"), "--probe", temporary])
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__": unittest.main(verbosity=2)
