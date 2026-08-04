#!/usr/bin/env python3
import csv
import os
import re
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(ROOT, ".."))
HW_H = os.path.join(REPO, "simulation/src/point-to-point/model/rdma-hw.h")
HW_CC = os.path.join(REPO, "simulation/src/point-to-point/model/rdma-hw.cc")
QP_H = os.path.join(REPO, "simulation/src/point-to-point/model/rdma-queue-pair.h")
THIRD = os.path.join(REPO, "simulation/scratch/third.cc")


class StableHandoffStatic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(HW_H) as f: cls.h = f.read()
        with open(HW_CC) as f: cls.cc = f.read()
        with open(QP_H) as f: cls.qp = f.read()
        with open(THIRD) as f: cls.third = f.read()

    def test_cc_modes_are_unique_and_frozen(self):
        pairs = re.findall(r"(CC_MODE_[A-Z0-9_]+)\s*=\s*(\d+)", self.h)
        values = {}
        for name, value in pairs:
            self.assertNotIn(int(value), values,
                             "%s conflicts with %s" % (name, values.get(int(value))))
            values[int(value)] = name
        self.assertEqual(values[25], "CC_MODE_CBAP_FULL_SCOPED_RATEFLOOR_FIX")
        self.assertEqual(values[26], "CC_MODE_CBAP_FULL_STABLE_HANDOFF")
        self.assertEqual(values[15], "CC_MODE_BOP_QB")

    def test_phase_ids_preserve_v13(self):
        expected = {"CBAP_DISABLED": 0, "CBAP_PREPARE": 1,
                    "CBAP_ADMISSION_HOLD": 2, "CBAP_TRACKING": 3,
                    "CBAP_RECOVERY": 4, "CBAP_FINISHED": 5,
                    "CBAP_HANDOFF_PENDING": 6, "CBAP_BASE_CC": 7}
        found = dict((n, int(v)) for n, v in
                     re.findall(r"(CBAP_[A-Z_]+)\s*=\s*(\d+)", self.qp))
        for name, value in expected.items():
            self.assertEqual(found[name], value)

    def test_structural_eligibility_is_fixed(self):
        self.assertIn("config.handoffStableEpochsRequired == 2", self.cc)
        self.assertIn("2 * s_cbapConfig.controlEpochNs", self.cc)
        self.assertIn("2 * measuredRtt", self.cc)
        self.assertIn("port.queueBytes > qLow", self.cc)
        self.assertIn("CC_MODE_CBAP_FULL_STABLE_HANDOFF", self.cc)
        forbidden = ("message size threshold", "fanin threshold",
                     "collective_name")
        for text in forbidden:
            self.assertNotIn(text, self.cc.lower())

    def test_atomic_one_way_and_dcqcn_reuse(self):
        body = self.cc[self.cc.index("ExecuteCbapBatchHandoff"):]
        self.assertIn("!batch.handoffOccurred", body)
        self.assertIn("qp->mlx.m_targetRate = DataRate(row.cbapAppliedRateBefore)", body)
        self.assertIn("qp->m_rate = DataRate(row.cbapAppliedRateBefore)", body)
        self.assertIn("qp->cbap.phase = RdmaQueuePair::CBAP_BASE_CC", body)
        self.assertIn("qp->cbap.exactGrantPacing = false", body)
        self.assertIn("&RdmaHw::RateIncEventTimerMlx, flow.hw, qp", body)
        self.assertIn("RecordFirstDcqcnUpdate", self.cc)
        self.assertIn("cnp_received_mlx(qp)", self.cc)
        self.assertNotIn("CBAP_BASE_CC = 3", self.qp)

    def test_no_catchup_schedule(self):
        body = self.cc[self.cc.index("ExecuteCbapBatchHandoff"):]
        self.assertIn("std::max(now, safeNext)", body)
        self.assertIn("row.nextTxBeforeNs > next", body)
        self.assertIn("catchupBurstDetected", body)

    def test_outputs_and_config_are_wired(self):
        for key in ("CBAP_HANDOFF_SUMMARY_FILE", "CBAP_HANDOFF_FLOW_FILE",
                    "CBAP_CONTROLLER_OWNERSHIP_FILE",
                    "CBAP_CONTROL_MESSAGE_FILE", "CBAP_HANDOFF_ENABLE"):
            self.assertIn(key, self.third)

    def test_manifests_have_exact_counts(self):
        with open(os.path.join(ROOT, "configs", "semantic_manifest.csv")) as f:
            semantic = list(csv.DictReader(f))
        with open(os.path.join(ROOT, "configs", "validation_manifest.csv")) as f:
            validation = list(csv.DictReader(f))
        self.assertEqual(len(semantic), 7)
        self.assertEqual(len(validation), 30)
        self.assertEqual(sum(int(x["cc_mode"]) == 26 for x in validation), 6)

    def test_scripts_do_not_run_during_generation(self):
        with open(os.path.join(ROOT, "scripts", "generate_framework.py")) as f:
            generator = f.read()
        self.assertNotIn("--run", generator)
        self.assertNotIn("waf", generator)

    def test_mode26_is_registered_for_round_mode(self):
        match = re.search(
            r"if \(round_mode\).*?\(cc_mode >= 11 && cc_mode <= 26\)\)\)"
            r"\s*ConfigError\(\"ROUND_MODE CC_MODE is not registered\"\)",
            self.third, re.S)
        self.assertIsNotNone(match, "mode26 missing from ROUND_MODE registry")

    def test_redundant_unbounded_packet_trace_is_disabled(self):
        with open(os.path.join(ROOT, "scripts", "prepare_run.py")) as f:
            prepare = f.read()
        self.assertIn('"CBAP_PACKET_TRACE_FILE": "/dev/null"', prepare)
        self.assertIn('"CBAP_TX_EVENT_FILE"', prepare)
        self.assertIn('"CBAP_HANDOFF_FLOW_FILE"', prepare)

    def test_collective_completion_scope_is_explicit(self):
        with open(os.path.join(ROOT, "scripts", "check_outputs.py")) as f:
            checker = f.read()
        with open(os.path.join(ROOT, "scripts", "common.sh")) as f:
            common = f.read()
        with open(os.path.join(ROOT, "scripts",
                               "analyze_handoff_results.py")) as f:
            analysis = f.read()
        self.assertIn('scenario.get("pending_flow_ids", [])', checker)
        self.assertIn("missing incumbent workload rounds", checker)
        self.assertIn('$V14_ROOT/scripts/collect_run_metrics.py', common)
        self.assertIn('pending_collective_only', analysis)

    def test_pacing_audit_stops_at_handoff_boundary(self):
        self.assertIn(
            "qp->cbap.exactGrantPacing && !qp->cbap.handedOff",
            self.cc)
        with open(os.path.join(
                ROOT, "scripts", "analyze_handoff_semantic.py")) as stream:
            analyzer = stream.read()
        self.assertIn("handoff occurred during forced recovery", analyzer)
        self.assertIn("completed_before_handoff", analyzer)
        with open(os.path.join(ROOT, "scripts", "check_outputs.py")) as stream:
            checker = stream.read()
        self.assertIn('"pacing_violations"', checker)
        self.assertIn('int(meta["cc_mode"]) in (22, 23, 24, 25, 26)',
                      checker)


if __name__ == "__main__":
    unittest.main()
