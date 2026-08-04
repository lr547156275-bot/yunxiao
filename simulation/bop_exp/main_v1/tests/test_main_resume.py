import os
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class ResumeTest(unittest.TestCase):
    def test_resume_and_safety_controls(self):
        common = open(os.path.join(ROOT, "scripts", "common.sh")).read()
        for token in ("completed.flag", "hash-mismatched", "FORCE_RERUN",
                      "MIN_FREE_GB", "RUN_TIMEOUT_MIN", "timeout",
                      "KEEP_RAW", "JOBS", "wait -n", "SIGINT",
                      "main_clear_outputs", "seed%$'\\r'"):
            self.assertIn(token, common)
        self.assertTrue(os.path.exists(os.path.join(ROOT,
                                                   "resume_failed.sh")))

    def test_orchestration_fixes_do_not_invalidate_simulation_results(self):
        checker = open(os.path.join(
            ROOT, "scripts", "check_main_outputs.py")).read()
        for path in ("config/run_manifest.csv",
                     "scripts/check_main_outputs.py",
                     "scripts/common.sh"):
            self.assertIn('"%s"' % path, checker)


if __name__ == "__main__":
    unittest.main()
