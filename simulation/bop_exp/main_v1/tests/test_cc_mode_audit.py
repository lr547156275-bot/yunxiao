import csv
import os
import re
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SIM = os.path.abspath(os.path.join(ROOT, "..", ".."))


class CcModeAuditTest(unittest.TestCase):
    def test_registry_modes_and_dispatch(self):
        with open(os.path.join(ROOT, "config", "algorithm_registry.csv")) as h:
            registry = {row["algorithm_name"]: int(row["cc_mode"])
                        for row in csv.DictReader(h)}
        expected = {
            "pfc_only": 0, "dcqcn": 1, "hpcc_int": 3, "timely": 7,
            "dctcp": 8, "crfm_gate": 12, "bop": 13, "bop_qb": 15,
            "dcqcn_wire_equalized": 17,
        }
        self.assertEqual(expected, registry)
        with open(os.path.join(SIM, "src", "point-to-point", "model",
                               "rdma-hw.h")) as handle:
            header = handle.read()
        for symbol, value in (("CRFM_GATE", 12), ("BOP", 13),
                              ("BOP_QB", 15),
                              ("DCQCN_WIRE_EQUALIZED", 17)):
            self.assertRegex(header, r"CC_MODE_%s\s*=\s*%d" %
                             (symbol, value))
        with open(os.path.join(SIM, "src", "point-to-point", "model",
                               "rdma-hw.cc")) as handle:
            source = handle.read()
        for handler in ("HandleAckHp", "HandleAckTimely",
                        "HandleAckDctcp", "HandleAckCrfm",
                        "PlanRoundGroup"):
            self.assertIn(handler, source)

    def test_forbidden_modes_absent_from_manifest(self):
        with open(os.path.join(ROOT, "config", "run_manifest.csv")) as handle:
            manifest = handle.read()
        for forbidden in ("bop_qc", "bop_qb_max", "bop_qb_prt",
                          "bop_qb_oracle_q0", "bop_wc"):
            self.assertNotIn("," + forbidden + ",", manifest)


if __name__ == "__main__":
    unittest.main()
