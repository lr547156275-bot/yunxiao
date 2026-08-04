#!/usr/bin/env python3
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from closlib import CASES, input_hashes, scenario_specs


class PathHashTest(unittest.TestCase):
    def test_seed_and_algorithm_contract(self):
        for spec in scenario_specs():
            hashes = []
            for seed in (1, 2, 3):
                case = os.path.join(CASES, spec["scenario"],
                                    "seed_%d" % seed)
                current = input_hashes(case)
                with open(os.path.join(case, "input_hashes.json")) as handle:
                    recorded = json.load(handle)
                self.assertEqual(current, recorded)
                with open(os.path.join(
                        case, "multilink_links.txt")) as handle:
                    link_count = int(handle.readline())
                    legal_links = {int(handle.readline().split()[0])
                                   for _ in range(link_count)}
                with open(os.path.join(
                        case, "multilink_paths.txt")) as handle:
                    path_count = int(handle.readline())
                    for _ in range(path_count):
                        values = [int(value)
                                  for value in handle.readline().split()]
                        self.assertEqual(values[1], len(values[2:]))
                        self.assertTrue(set(values[2:]) <= legal_links)
                        self.assertTrue(2 <= values[1] <= 4)
                hashes.append((current["fixed_paths.txt"],
                               current["rounds.txt"]))
            self.assertEqual(len(set(hashes)), 3)


if __name__ == "__main__":
    unittest.main()
