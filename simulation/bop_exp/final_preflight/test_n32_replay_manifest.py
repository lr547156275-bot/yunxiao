#!/usr/bin/env python3
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = HERE.parents[1]
CHECKER = SIM / "bop_exp/main_v2/scripts/check_n32_dcqcn_replay.py"
RUNNER = SIM / "bop_exp/main_v2/run_n32_dcqcn_replay.sh"


def load_checker():
    spec = importlib.util.spec_from_file_location("n32_checker", CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    checker = load_checker()
    entries = checker.manifest()
    assert len(entries) == 3
    assert {int(row["seed"]) for row in entries} == {1, 2, 3}
    assert {row["scenario"] for row in entries} == {"n32_64k_g50"}
    assert {row["algorithm"] for row in entries} == {"dcqcn"}
    assert {row["cc_mode"] for row in entries} == {"1"}
    assert len({row["rounds_sha256"] for row in entries}) == 3
    for entry in entries:
        source = checker.SIM / entry["source_run"]
        assert checker.validate_inputs(entry, source) == []
    runner = RUNNER.read_text()
    assert "prepare_main_run.py" not in runner
    assert "copy_exact_inputs" in runner
    assert "for seed in 1 2 3" in runner
    assert "group_rct_delta_gt_1ns" in CHECKER.read_text()
    assert "queue_max_delta_gt_1B" in CHECKER.read_text()
    assert "legacy_213us_excluded" in runner
    print("PASS n32 DCQCN replay exact-input manifest seeds=1,2,3")


if __name__ == "__main__":
    main()
