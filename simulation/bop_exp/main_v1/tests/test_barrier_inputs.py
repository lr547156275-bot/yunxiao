import os
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class BarrierInputTest(unittest.TestCase):
    def test_round_groups_and_same_qp_totals(self):
        for scenario in os.listdir(os.path.join(ROOT, "cases")):
            case = os.path.join(ROOT, "cases", scenario)
            rounds_path = os.path.join(case, "rounds.txt")
            flows_path = os.path.join(case, "flow.txt")
            if not os.path.isfile(rounds_path):
                continue
            with open(rounds_path) as handle:
                rows = [list(map(int, line.split()))
                        for line in handle.read().splitlines()[1:]]
            with open(flows_path) as handle:
                flows = [line.split()
                         for line in handle.read().splitlines()[1:]]
            by_flow = {}
            groups = {}
            for row in rows:
                flow_id, round_id, group_id, participants = row[:4]
                round_bytes = row[4]
                by_flow.setdefault(flow_id, 0)
                by_flow[flow_id] += round_bytes
                groups.setdefault(group_id, set()).add(flow_id)
                self.assertEqual(round_id, group_id)
                if round_id > 0:
                    self.assertGreaterEqual(row[5] + row[6], 0)
                self.assertEqual(row[7], flow_id)
            self.assertEqual(len(flows), len(by_flow))
            for flow_id, flow in enumerate(flows):
                self.assertEqual(int(flow[4]), by_flow[flow_id])
            for group_id, members in groups.items():
                expected = next(row[3] for row in rows
                                if row[2] == group_id)
                self.assertEqual(expected, len(members))


if __name__ == "__main__":
    unittest.main()
