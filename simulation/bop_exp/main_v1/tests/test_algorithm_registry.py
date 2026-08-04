import csv
import hashlib
import os
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SIM = os.path.abspath(os.path.join(ROOT, "..", ".."))


class RegistryTest(unittest.TestCase):
    def test_registry_matches_source(self):
        path = os.path.join(ROOT, "config", "algorithm_registry.csv")
        data = list(csv.DictReader(open(path)))
        self.assertEqual(9, len(data))
        self.assertEqual(len(data), len({x["cc_mode"] for x in data}))
        names = {x["algorithm_name"] for x in data}
        self.assertEqual({"pfc_only", "dctcp", "dcqcn", "timely", "hpcc_int",
                          "bop_qb", "crfm_gate", "bop",
                          "dcqcn_wire_equalized"}, names)
        for row in data:
            source = os.path.join(SIM, row["implementation_file"])
            actual = hashlib.sha256(open(source, "rb").read()).hexdigest()
            self.assertEqual(actual, row["source_hash"])
        qb = next(x for x in data if x["algorithm_name"] == "bop_qb")
        self.assertEqual("15", qb["cc_mode"])
        self.assertEqual("1", qb["frozen"])
        self.assertEqual("1", next(x for x in data
                                   if x["algorithm_name"] == "pfc_only")[
                                       "baseline_only"])


if __name__ == "__main__":
    unittest.main()
