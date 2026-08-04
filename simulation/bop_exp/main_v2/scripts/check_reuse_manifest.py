#!/usr/bin/env python3
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    subprocess.check_call([sys.executable, str(
        ROOT / "scripts/build_main_v2.py")])
    rows = list(csv.DictReader(open(ROOT / "config/reuse_manifest.csv")))
    assert len(rows) == 273, len(rows)
    allowed = sum(row["reuse_allowed"] == "true" for row in rows)
    rejected = [row for row in rows if row["reuse_allowed"] != "true"]
    print("checked=%d reuse_allowed=%d rejected=%d" %
          (len(rows), allowed, len(rejected)))
    return 0 if not rejected else 1


if __name__ == "__main__":
    raise SystemExit(main())
