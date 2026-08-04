#!/usr/bin/env python3
import csv
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = HERE.parents[1]
CHECKER = SIM / "bop_exp/main_v2/scripts/check_semantic_audit.py"


def load_checker():
    spec = importlib.util.spec_from_file_location("pfc_checker", CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    checker = load_checker()
    assert checker.validate_static() == []
    rows = list(csv.DictReader(open(HERE / "pfc_audit_manifest.csv")))
    assert len(rows) == 9
    assert {(row["scenario"], row["algorithm"]) for row in rows} == \
        set(checker.EXPECTED)
    assert {row["seed"] for row in rows} == {"1"}
    assert sum(row["pfc_runtime_enable"] == "0" for row in rows) == 3
    contract = (HERE / "pfc_audit_contract.md").read_text()
    for token in checker.EVENTS:
        assert "`%s`" % token in contract
    assert "missing" in contract.lower()
    assert "never replaced with zero" in contract
    assert "BEgressQueue" in contract and "SwitchMmu" in contract
    assert "GetNextQindex(m_paused)" in contract
    topology = SIM / (
        "bop_exp/main_v1/runs/msg_64k_n16_g50/pfc_only/seed_1/"
        "topology.txt")
    peers = checker.topology_peer_ports(topology)
    assert peers[(18, 2)] == (19, 2)
    synthetic = []
    specs = [
        ("pause_generated", 18, 2, 100),
        ("pause_received", 19, 2, 101),
        ("sender_paused", 19, 2, 101),
        ("resume_generated", 18, 2, 200),
        ("resume_received", 19, 2, 201),
        ("sender_resumed", 19, 2, 201),
    ]
    for event, node, port, timestamp in specs:
        synthetic.append({
            "event_type": event, "node_id": str(node),
            "device_id": str(port), "port_id": str(port),
            "priority_or_pg": "3", "timestamp_ns": str(timestamp),
        })
    summary = {field: 1 for field in checker.SUMMARY_COUNTER.values()}
    assert checker.validate_event_chain(synthetic, summary, topology) == []
    print("PASS PFC event contract matrix=9 missing-events-not-zero")


if __name__ == "__main__":
    main()
