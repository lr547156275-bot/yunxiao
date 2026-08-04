#!/usr/bin/env python3
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from closlib import (ECN_THRESHOLD_BYTES, LINK_BPS, build_groups,
                     materialize, multilink_plan, scenario_specs)


class MultilinkCreditTest(unittest.TestCase):
    def test_every_link_bound(self):
        flows = {0: 101, 1: 203, 2: 307}
        paths = {0: [0], 1: [0, 1], 2: [1]}
        links = {
            0: {"capacity": 100000, "ecn_threshold": 4096, "q0": 0},
            1: {"capacity": 100000, "ecn_threshold": 4096, "q0": 100},
        }
        plan = multilink_plan(flows, paths, links,
                              {flow: 100000 for flow in flows},
                              packet_bytes=64)
        for state in plan["links"].values():
            self.assertLessEqual(state["credit"], state["room"])
        self.assertTrue(0 <= plan["alpha"] <= 1)

    def test_all_formal_group_constraints(self):
        for spec in scenario_specs():
            data = materialize(spec, 1)
            flow_bytes_by_group = {}
            for row in data["rounds"]:
                flow_id, _round_id, group_id, _participants, amount = row[:5]
                flow_bytes_by_group.setdefault(group_id, {})[flow_id] = amount
            links = {
                row[0]: {"capacity": LINK_BPS,
                         "ecn_threshold": ECN_THRESHOLD_BYTES, "q0": 0}
                for row in data["model"]["controlled_links"]}
            for flow_bytes in flow_bytes_by_group.values():
                paths = {flow_id: data["paths"][flow_id]
                         for flow_id in flow_bytes}
                rates = {flow_id: LINK_BPS for flow_id in flow_bytes}
                plan = multilink_plan(flow_bytes, paths, links, rates)
                for link_id, state in plan["links"].items():
                    self.assertLessEqual(state["credit"], state["room"])
                    rate_sum = sum(plan["rates"][flow_id]
                                   for flow_id in flow_bytes
                                   if link_id in paths[flow_id])
                    self.assertLessEqual(rate_sum, LINK_BPS)


if __name__ == "__main__":
    unittest.main()
