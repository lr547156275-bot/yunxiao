import csv
import hashlib
import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from mainlib import scenarios, write_round_inputs


class MainManifestTest(unittest.TestCase):
    def test_counts_and_uniqueness(self):
        scenarios = list(csv.DictReader(open(os.path.join(
            ROOT, "config", "main_scenarios.csv"))))
        manifest = list(csv.DictReader(open(os.path.join(
            ROOT, "config", "run_manifest.csv"))))
        self.assertEqual(15, len(scenarios))
        self.assertEqual(318, len(manifest))
        self.assertEqual(318, len({x["run_id"] for x in manifest}))
        for seed in ("1", "2", "3"):
            selected = [x for x in manifest if x["seed"] == seed]
            self.assertEqual(106, len(selected))
            self.assertEqual(90, sum(x["section"] == "main" for x in selected))
        keys = [(x["senders"], x["rounds"], x["compute_gap_us"],
                 x["min_message_bytes"], x["max_message_bytes"],
                 x["sweep"]) for x in scenarios]
        self.assertEqual(len(keys), len(set(keys)))

    def test_heterogeneous_payload(self):
        scenarios = list(csv.DictReader(open(os.path.join(
            ROOT, "config", "main_scenarios.csv"))))
        hetero = [x for x in scenarios if x["scenario"].startswith("hetero_")]
        self.assertEqual(3, len(hetero))
        self.assertTrue(all(int(x["total_group_payload_bytes"]) == 2097152
                            for x in hetero))

    def test_seed_changes_rounds(self):
        with tempfile.TemporaryDirectory() as temporary:
            hashes = []
            for seed in (1, 2, 3):
                path = os.path.join(temporary, str(seed))
                os.makedirs(path)
                write_round_inputs(path, scenarios()["msg_64k_n16_g50"],
                                   seed)
                hashes.append(hashlib.sha256(open(os.path.join(
                    path, "rounds.txt"), "rb").read()).hexdigest())
            self.assertEqual(3, len(set(hashes)))


if __name__ == "__main__":
    unittest.main()
