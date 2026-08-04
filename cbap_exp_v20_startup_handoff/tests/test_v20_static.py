#!/usr/bin/env python3
import csv
import os
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class V20StaticTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "simulation", "src", "point-to-point",
                               "model", "rdma-hw.cc")) as stream:
            cls.hw = stream.read()
        with open(os.path.join(ROOT, "simulation", "src", "point-to-point",
                               "model", "rdma-hw.h")) as stream:
            cls.header = stream.read()

    def test_modes_are_new_and_distinct(self):
        self.assertIn("CC_MODE_CBAP_V20_STARTUP_HANDOFF_DCQCN = 28", self.header)
        self.assertIn("CC_MODE_CBAP_V20_STARTUP_HANDOFF_HPCC = 29", self.header)

    def test_no_scenario_or_message_size_switch(self):
        body = self.hw[self.hw.index("void RdmaHw::PlanCbapV20Batch"):]
        body = body[:body.index("void RdmaHw::PlanCbapBatch")]
        self.assertNotIn("s_cbapConfig.scenario", body)
        self.assertNotIn("round.roundBytes ==", body)
        self.assertNotIn("round.roundBytes <", body)

    def test_one_shot_exit_and_no_legacy_tracking(self):
        self.assertIn("EvaluateCbapV20Batches(now);", self.hw)
        self.assertIn("!flow->second.qp->cbap.v20Enabled", self.hw)
        self.assertIn("CBAP_BASE_CC_ONLY", self.hw)
        self.assertIn("v20PostHandoffCbapWriteCount", self.hw)

    def test_missing_or_stale_shared_summary_is_complex(self):
        self.assertIn("sharedSummaryUnavailable", self.hw)
        self.assertIn("shared_path_summary_missing_or_stale", self.hw)
        self.assertIn("anyPostReleaseFeedback", self.hw)

    def test_zero_budget_dcqcn_handoff_reschedules(self):
        timer = self.hw[self.hw.index(
            "void RdmaHw::RateIncEventTimerMlx"):]
        timer = timer[:timer.index("void RdmaHw::RateIncEventMlx")]
        self.assertIn("CBAP_BASE_CC_ONLY", timer)
        self.assertIn("after > 0 && after != before", timer)
        self.assertIn("ChangeRate(q, DataRate(after));", timer)
        self.assertIn("InvalidateAndRescheduleRdma();", timer)

    def test_lease_observes_same_timestamp_feedback(self):
        self.assertIn("FinalizeCbapV20Lease", self.hw)
        self.assertIn("ScheduleNow(&RdmaHw::FinalizeCbapV20Lease", self.hw)

    def test_manifest_counts(self):
        with open(os.path.join(ROOT, "cbap_exp_v20_startup_handoff",
                               "configs", "semantic_manifest.csv")) as stream:
            semantic = list(csv.DictReader(stream))
        with open(os.path.join(ROOT, "cbap_exp_v20_startup_handoff",
                               "configs", "pareto_manifest.csv")) as stream:
            pareto = list(csv.DictReader(stream))
        self.assertEqual(len(semantic), 8)
        self.assertEqual(len(pareto), 30)
        self.assertEqual(sorted(set(float(r["queue_target_fraction"])
                                    for r in pareto)),
                         [0, .125, .25, .5, .75])

    def test_frozen_v13_identity_present(self):
        self.assertIn("CC_MODE_CBAP_FULL_SCOPED_RATEFLOOR_FIX = 25", self.header)
        self.assertIn('"v13_shadow_only"', self.hw)


if __name__ == "__main__":
    unittest.main()
