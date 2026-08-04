#!/usr/bin/env python3
"""Static guards for the CBAP-v1 admission/credit repair.

These tests inspect source and generated manifests only.  They never invoke waf
or an ns-3 executable.
"""
import csv
import gzip
import importlib.util
import os
import re
import tempfile
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
V1 = os.path.join(ROOT, "cbap_exp_v1_fix")


def read(relative):
    with open(os.path.join(ROOT, relative), encoding="utf-8") as stream:
        return stream.read()


class StaticCbapRepairTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hw_h = read("simulation/src/point-to-point/model/rdma-hw.h")
        cls.hw_cc = read("simulation/src/point-to-point/model/rdma-hw.cc")
        cls.qp_cc = read(
            "simulation/src/point-to-point/model/rdma-queue-pair.cc")
        cls.device_cc = read(
            "simulation/src/point-to-point/model/qbb-net-device.cc")
        cls.third = read("simulation/scratch/third.cc")

    def test_frozen_bop_qb_mode_is_15(self):
        self.assertRegex(self.hw_h, r"CC_MODE_BOP_QB\s*=\s*15\s*,")

    def test_post_release_freshness_uses_sample_and_delivery(self):
        body = self.hw_cc.split(
            "bool RdmaHw::HasCompletePostReleaseFeedback", 1)[1].split(
                "bool RdmaHw::HasPostReleaseEmergencyEvidence", 1)[0]
        self.assertIn("link.latest.sampleTimeNs <= release", body)
        self.assertIn("link.latest.deliveryTimeNs <= release", body)
        self.assertIn("return !path.empty()", body)

    def test_admission_hold_blocks_ordinary_tracking(self):
        body = self.hw_cc.split("void RdmaHw::RecomputeCbapTracking", 1)[1]
        hold = body.split("if (qp->cbap.phase == ", 1)[1]
        self.assertIn("!allFresh", hold)
        self.assertIn("HasPostReleaseEmergencyEvidence", hold)
        self.assertIn("continue;", hold)
        self.assertIn("ExitCbapAdmission(qp, completeDelivery)", body)

    def test_credit_gate_is_admission_only_everywhere(self):
        required = ("cbap.fullCredit", "cbap.creditGateActive",
                    "cbap.phase != CBAP_ADMISSION_HOLD")
        for token in required:
            self.assertIn(token, self.qp_cc)
        packet_gate = self.hw_cc.split(
            "if (qp->cbap.enabled && qp->cbap.fullCredit", 1)[1].split(
                "// update state", 1)[0]
        self.assertIn("qp->cbap.creditGateActive", packet_gate)
        self.assertIn("CBAP_ADMISSION_HOLD", packet_gate)
        exit_body = self.hw_cc.split("void RdmaHw::ExitCbapAdmission", 1)[1]
        self.assertIn("qp->cbap.creditGateActive = false", exit_body)

    def test_sender_event_types_and_real_send_hook_exist(self):
        for event in ("TX_SCHEDULE", "TX_SEND", "TX_RESCHEDULE",
                      "TX_CANCEL_OR_INVALIDATE"):
            self.assertIn('"%s"' % event, self.third)
        sent = self.hw_cc.split("void RdmaHw::PktSent", 1)[1].split(
            "void RdmaHw::UpdateNextAvail", 1)[0]
        self.assertIn("CBAP_TX_SEND", sent)
        self.assertIn("Simulator::Now().GetTimeStep()", sent)
        self.assertIn("pacingViolationCount++", sent)

    def test_cbap_reschedule_is_explicit_and_scoped(self):
        self.assertIn("void QbbNetDevice::InvalidateAndRescheduleRdma",
                      self.device_cc)
        setter = self.hw_cc.split("void RdmaHw::SetCbapRate", 1)[1].split(
            "bool RdmaHw::HasCompletePostReleaseFeedback", 1)[0]
        self.assertIn("InvalidateAndRescheduleRdma", setter)
        self.assertIn("CBAP_TX_CANCEL_OR_INVALIDATE", setter)
        self.assertIn("CBAP_TX_RESCHEDULE", setter)

    def test_required_csv_audit_fields_exist(self):
        fields = (
            "admission_enter_ns", "admission_exit_ns", "first_data_tx_ns",
            "first_post_release_sample_ns",
            "first_complete_fresh_feedback_ns", "first_fresh_feedback_ns",
            "initial_admit_rate_bps", "actual_admission_mean_rate_bps",
            "bytes_sent_before_fresh_feedback",
            "rate_updates_before_first_tx",
            "ordinary_rate_updates_during_admission",
            "emergency_rate_updates_during_admission",
            "credit_gate_enter_ns", "credit_gate_exit_ns",
            "credit_remaining_at_admission_exit",
            "tracking_actual_rate_bps", "tracking_current_rate_bps",
            "tracking_base_rate_bps", "pacing_violations")
        for field in fields:
            self.assertIn(field, self.third)


class GeneratedMatrixTest(unittest.TestCase):
    def rows(self, name):
        with open(os.path.join(V1, "config", name), newline="") as stream:
            return list(csv.DictReader(stream))

    def test_semantic_matrix_is_exactly_20(self):
        rows = self.rows("semantic_manifest.csv")
        self.assertEqual(20, len(rows))
        self.assertEqual({"1"}, {row["seed"] for row in rows})
        self.assertEqual(4, len({(row["scenario"], row["subcase"])
                                for row in rows}))
        self.assertEqual(5, len({row["algorithm"] for row in rows}))

    def test_formal_matrix_is_exactly_84(self):
        rows = self.rows("formal_manifest.csv")
        self.assertEqual(84, len(rows))
        self.assertEqual({"1", "2", "3"}, {row["seed"] for row in rows})
        self.assertEqual(4, len({(row["scenario"], row["subcase"])
                                for row in rows}))
        self.assertEqual(7, len({row["algorithm"] for row in rows}))
        self.assertNotIn("e3_victim_flow", {row["scenario"] for row in rows})

    def test_resume_checker_accepts_successfully_gzipped_detail(self):
        path = os.path.join(V1, "scripts", "check_outputs.py")
        spec = importlib.util.spec_from_file_location("v1_check_outputs", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            raw = os.path.join(directory, "cbap_tx_events.csv")
            with gzip.open(raw + ".gz", "wt") as stream:
                stream.write("event\nTX_SEND\n")
            self.assertEqual(raw + ".gz", module.existing(raw))
            self.assertEqual("TX_SEND", module.csv_rows(raw)[0]["event"])


if __name__ == "__main__":
    unittest.main()
