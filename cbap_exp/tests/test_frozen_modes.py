#!/usr/bin/env python3
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
header = open(os.path.join(
    ROOT, "simulation/src/point-to-point/model/rdma-hw.h")).read()
expected = {
    "CC_MODE_BOP_QB": 15,
    "CC_MODE_BOP_QB_MAX": 16,
    "CC_MODE_DCQCN_WIRE_EQUALIZED": 17,
    "CC_MODE_BOP_QB_ORACLE_Q0": 18,
    "CC_MODE_BOP_QB_PRT": 19,
    "CC_MODE_CBAP_INDEPENDENT": 20,
    "CC_MODE_CBAP_INIT_ONLY": 21,
    "CC_MODE_CBAP_RATE_ONLY": 22,
    "CC_MODE_CBAP_FULL": 23,
}
for name, value in expected.items():
    assert re.search(r"\b%s\s*=\s*%d\b" % (name, value), header)
source = open(os.path.join(
    ROOT, "simulation/src/point-to-point/model/rdma-hw.cc")).read()
assert "return mode == CC_MODE_BOP_QB || mode ==" in source
assert "mode >= CC_MODE_CBAP_INDEPENDENT" in source
switch = open(os.path.join(
    ROOT, "simulation/src/point-to-point/model/switch-node.cc")).read()
uses = switch[switch.index("bool SwitchNode::UsesHpccInt"):
              switch.index("bool SwitchNode::FixedPathKey")]
assert "20" not in uses and "21" not in uses and "22" not in uses and \
       "23" not in uses
print("PASS frozen mode map")
