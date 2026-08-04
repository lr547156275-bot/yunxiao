import argparse
import json
import os
import shutil
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS = os.path.join(ROOT, "scripts")
import sys
sys.path.insert(0, SCRIPTS)

from mainlib import registry
from prepare_main_run import prepare


class PrepareInputsTest(unittest.TestCase):
    def test_runner_uses_per_run_working_directory(self):
        common = os.path.join(ROOT, "scripts", "common.sh")
        with open(common) as handle:
            text = handle.read()
        self.assertIn('python2 ./waf --cwd="$run_dir"', text)

    def test_same_seed_inputs_match_across_algorithms(self):
        temporary = tempfile.mkdtemp(prefix="main_v1_prepare_")
        try:
            comparable = None
            for algorithm in sorted(registry()):
                run_dir = os.path.join(temporary, algorithm)
                args = argparse.Namespace(
                    scenario="msg_64k_n16_g50", algorithm=algorithm,
                    seed=2, run_dir=run_dir, min_free_gb=0)
                prepare(args)
                with open(os.path.join(run_dir, "run_meta.json")) as handle:
                    meta = json.load(handle)
                current = tuple(meta["input_hashes"][name] for name in (
                    "topology.txt", "flow.txt", "rounds.txt",
                    "fixed_paths.txt", "trace.txt"))
                if comparable is None:
                    comparable = current
                self.assertEqual(comparable, current)
                with open(os.path.join(run_dir, "config.txt")) as handle:
                    config = handle.read()
                self.assertIn("CC_MODE %s\n" %
                              registry()[algorithm]["cc_mode"], config)
        finally:
            shutil.rmtree(temporary)


if __name__ == "__main__":
    unittest.main()
