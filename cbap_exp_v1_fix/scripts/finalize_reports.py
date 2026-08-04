#!/usr/bin/env python3
"""Create the v1-fix-only source patch and deterministic file inventory."""
import argparse
import difflib
import os


SOURCE_FILES = (
    "simulation/scratch/third.cc",
    "simulation/src/point-to-point/model/qbb-net-device.cc",
    "simulation/src/point-to-point/model/qbb-net-device.h",
    "simulation/src/point-to-point/model/rdma-hw.cc",
    "simulation/src/point-to-point/model/rdma-hw.h",
    "simulation/src/point-to-point/model/rdma-queue-pair.cc",
    "simulation/src/point-to-point/model/rdma-queue-pair.h",
)


def lines(path):
    with open(path, encoding="utf-8", errors="surrogateescape") as stream:
        return stream.readlines()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--baseline", required=True)
    args = parser.parse_args()
    report_dir = os.path.join(args.repo, "cbap_exp_v1_fix", "reports")
    os.makedirs(report_dir, exist_ok=True)
    chunks = []
    changed = []
    for relative in SOURCE_FILES:
        before = os.path.join(args.baseline, relative)
        after = os.path.join(args.repo, relative)
        delta = list(difflib.unified_diff(
            lines(before), lines(after), fromfile="a/" + relative,
            tofile="b/" + relative))
        if delta:
            chunks.extend(delta)
            changed.append(relative)
    with open(os.path.join(report_dir, "code_changes.patch"), "w",
              encoding="utf-8") as stream:
        stream.writelines(chunks)

    v1_files = []
    v1_root = os.path.join(args.repo, "cbap_exp_v1_fix")
    for base, dirs, files in os.walk(v1_root):
        dirs[:] = sorted(name for name in dirs if name != "__pycache__")
        for name in sorted(files):
            absolute = os.path.join(base, name)
            relative = os.path.relpath(absolute, args.repo)
            v1_files.append(relative)
    inventory = changed + sorted(v1_files)
    with open(os.path.join(report_dir, "files_changed.txt"), "w",
              encoding="utf-8") as stream:
        stream.write("\n".join(inventory) + "\n")
    print("source_files_changed=%d patch_lines=%d inventory=%d" %
          (len(changed), len(chunks), len(inventory)))


if __name__ == "__main__":
    main()
