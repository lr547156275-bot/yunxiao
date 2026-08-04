#!/usr/bin/env python3
from pathlib import Path

SIM = Path(__file__).resolve().parents[3]
third = (SIM / "scratch/third.cc").read_text()
switch = (SIM / "src/point-to-point/model/switch-node.cc").read_text()
device = (SIM / "src/point-to-point/model/qbb-net-device.cc").read_text()
assert 'BooleanValue(true)' in switch
assert 'if (!m_pfcEnabled)' in switch
assert 'PFC_RUNTIME_ENABLE' in third
assert 'pfc_event_trace.csv' in (
    SIM / "bop_exp/main_v2/scripts/prepare_semantic_audit.py").read_text()
for event in ("pause_generated", "pause_received", "sender_paused",
              "resume_generated", "resume_received", "sender_resumed"):
    assert event in third
assert 'GetPfcOccupancy' in switch
assert 'm_tracePfcSemantic' in device
assert 'queue_and_pfc_objects_identical' in third
assert 'PfcAuditQueueEvent' in third
print("PASS event-level PFC instrumentation")
