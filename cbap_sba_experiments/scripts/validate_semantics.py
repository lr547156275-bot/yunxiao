#!/usr/bin/env python3
import argparse
import csv
import json
import pathlib
import subprocess
import sys


REQUIRED = [
    "shared_link_atomic_grant",
    "two_bottlenecks_path_min",
    "zero_grant_hold_readmission",
    "single_handoff_applied_rate",
    "held_flow_never_dcqcn",
    "no_cbap_write_after_handoff",
]


def validate_reduced(root: pathlib.Path) -> dict:
    binary = root / "cbap_sba_experiments/tests/.build/cbap_sba_reduced_test"
    completed = subprocess.run(
        [str(binary)], text=True, capture_output=True, check=False
    )
    sys.stdout.write(completed.stdout)
    sys.stderr.write(completed.stderr)
    passed = {
        line.split(" ", 1)[1]
        for line in completed.stdout.splitlines()
        if line.startswith("PASS ")
    }
    missing = [name for name in REQUIRED if name not in passed]
    if completed.returncode or missing:
        raise RuntimeError(f"reduced semantic validation failed; missing={missing}")
    result = {"status": "PASS", "tests": REQUIRED}
    summary = root / "cbap_sba_experiments/summaries/reduced_validation.json"
    summary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def validate_smoke(run_dir: pathlib.Path) -> dict:
    event_file = run_dir / "cbap_sba_events.csv"
    if not event_file.is_file():
        raise RuntimeError("smoke run did not produce cbap_sba_events.csv")
    with event_file.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    initial = [
        row for row in rows
        if row["state_transition"] == "COLLECTING->STARTUP_SENDING"
    ]
    if len(initial) != 4:
        raise RuntimeError(f"expected four atomic startup grants, got {len(initial)}")
    grants = [int(row["grant_rate"]) for row in initial]
    applied = [int(row["applied_rate"]) for row in initial]
    if sum(grants) > 100_000_000_000:
        raise RuntimeError("smoke grant sum violates 100 Gbps conservation")
    if grants != [25_000_000_000] * 4 or applied != grants:
        raise RuntimeError(f"smoke exact grants/applied rates are wrong: {grants}")
    if any(rate in (0, 1) for rate in applied):
        raise RuntimeError("smoke contains a zero/fake sending rate")
    handoffs = [
        row for row in rows
        if row["state_transition"] == "STARTUP_SENDING->DCQCN_OWNED"
    ]
    if len(handoffs) != 4 or len({row["flow_id"] for row in handoffs}) != 4:
        raise RuntimeError("each positive flow must hand off exactly once")
    for row in handoffs:
        if int(row["first_feedback_time"]) < int(row["release_time"]):
            raise RuntimeError("smoke accepted pre-release feedback")
        if int(row["handoff_rate"]) != 25_000_000_000:
            raise RuntimeError("DCQCN was not initialized from applied rate")
    expected_chain = [
        "COLLECTING->STARTUP_SENDING",
        "STARTUP_SENDING->DCQCN_OWNED",
        "DCQCN_OWNED->FINISHED",
    ]
    for flow_id in {row["flow_id"] for row in initial}:
        chain = [
            row["state_transition"] for row in rows
            if row["flow_id"] == flow_id
        ]
        if chain != expected_chain:
            raise RuntimeError(
                f"post-handoff SBA transition detected for flow {flow_id}: {chain}"
            )
    result = {
        "status": "PASS",
        "run_dir": str(run_dir),
        "flow_count": 4,
        "grant_sum_bps": sum(grants),
        "per_flow_grant_bps": grants[0],
        "single_handoff_flow_count": len(handoffs),
    }
    (run_dir / "smoke_validation.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print("PASS ns3_smoke_atomic_exact_grant_and_single_handoff")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-dir", type=pathlib.Path)
    args = parser.parse_args()
    root = pathlib.Path(__file__).resolve().parents[2]
    try:
        if args.smoke_dir:
            validate_smoke(args.smoke_dir.resolve())
        else:
            validate_reduced(root)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
