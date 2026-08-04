import hashlib
import os
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SIM = os.path.abspath(os.path.join(ROOT, "..", ".."))


class FrozenSourceHashesTest(unittest.TestCase):
    def test_control_sources_unchanged(self):
        path = os.path.join(ROOT, "config", "frozen_source_hashes.sha256")
        with open(path) as handle:
            rows = [line.strip().split(None, 1) for line in handle if line.strip()]
        self.assertEqual(4, len(rows))
        for expected, relative in rows:
            with open(os.path.join(SIM, relative), "rb") as source:
                actual = hashlib.sha256(source.read()).hexdigest()
            self.assertEqual(expected, actual, relative)


if __name__ == "__main__":
    unittest.main()
