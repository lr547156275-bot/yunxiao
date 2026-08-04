#!/usr/bin/env python3
import csv
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    report = (HERE / "multilink_capability_report.md").read_text()
    verdicts = (
        "MULTILINK_NATIVE", "MULTILINK_TSTAR_ONLY",
        "SINGLE_BOTTLENECK_HARDCODED", "MULTILINK_AUDIT_INVALID",
    )
    present = [verdict for verdict in verdicts
               if ("`%s`" % verdict) in report]
    assert present == ["SINGLE_BOTTLENECK_HARDCODED"]
    source_map = list(csv.DictReader(open(HERE / "multilink_source_map.csv")))
    hardcoded = list(csv.DictReader(open(HERE / "hardcoded_bottlenecks.csv")))
    assert len(source_map) >= 8 and len(hardcoded) >= 5
    assert any(row["audit_item"] == "per_link_work" and
               row["support_status"] == "not_supported"
               for row in source_map)
    assert any(row["audit_item"] == "qb_single_queue_budget" and
               row["support_status"] == "not_supported"
               for row in source_map)
    hw = (SIM / "src/point-to-point/model/rdma-hw.cc").read_text()
    third = (SIM / "scratch/third.cc").read_text()
    assert "uint64_t capacity = owner->m_bopBottleneckBps;" in hw
    assert "double linkTime = isBopFamily ?" in hw
    assert "qbGroupCredit = std::min(qbQueueRoom, totalBytes);" in hw
    assert 'key.compare("BOP_BOTTLENECK_BPS")' in third
    frozen = SIM / "bop_exp/main_v1/config/frozen_source_hashes.sha256"
    for line in frozen.read_text().splitlines():
        expected, relative = line.split(None, 1)
        assert sha(SIM / relative.strip()) == expected
    print("PASS multilink verdict=SINGLE_BOTTLENECK_HARDCODED")


if __name__ == "__main__":
    main()
