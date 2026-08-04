#!/usr/bin/env python3
"""Create the bounded CBAP-v1 result archive from existing files only."""
import datetime
import hashlib
import os
import shutil
import subprocess
import tarfile


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(ROOT, ".."))
DETAIL_NAMES = {
    "cbap_packet_trace.csv", "cbap_packet_trace.csv.gz",
    "selected_flow_timeseries.csv", "selected_flow_timeseries.csv.gz",
    "selected_link_timeseries.csv", "selected_link_timeseries.csv.gz",
    "cbap_tx_events.csv", "cbap_tx_events.csv.gz",
    "cbap_rate_transitions.csv", "cbap_port_summary.csv",
}


def files_under(path):
    if not os.path.isdir(path):
        return []
    result = []
    for base, dirs, files in os.walk(path):
        dirs[:] = sorted(name for name in dirs
                         if name != "__pycache__" and name != "build")
        for name in sorted(files):
            if name.endswith((".o", ".obj", ".pyc", ".core")) or \
                    name == "core":
                continue
            result.append(os.path.join(base, name))
    return result


def prepare_metadata():
    reports = os.path.join(ROOT, "reports")
    configs = os.path.join(ROOT, "configs")
    os.makedirs(reports, exist_ok=True)
    os.makedirs(configs, exist_ok=True)
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    status = subprocess.check_output(
        ["git", "status", "--short"], cwd=REPO, text=True)
    with open(os.path.join(reports, "git_commit.txt"), "w") as stream:
        stream.write(commit + "\n")
    with open(os.path.join(reports, "git_status.txt"), "w") as stream:
        stream.write(status)
    for name in ("semantic_manifest.csv", "formal_manifest.csv"):
        shutil.copy2(os.path.join(ROOT, "config", name),
                     os.path.join(configs, name))
    cases = os.path.join(ROOT, "cases")
    for base, _, files in os.walk(cases):
        if "config.txt" not in files:
            continue
        relative = os.path.relpath(base, cases).replace(os.sep, "__")
        shutil.copy2(os.path.join(base, "config.txt"),
                     os.path.join(configs, relative + "__config.txt"))


def select_files():
    included, excluded = set(), []
    for name in ("reports", "processed", "figures", "configs", "scripts",
                 "preflight", "codex_logs", "runs_semantic"):
        included.update(files_under(os.path.join(ROOT, name)))
    # Manual build/run logs stored directly below the task root.
    for name in os.listdir(ROOT):
        if (name.startswith("manual_build_") or
                name.startswith("semantic_run_")) and name.endswith(".log"):
            included.add(os.path.join(ROOT, name))
    formal = os.path.join(ROOT, "runs_formal")
    for path in files_under(formal):
        relative = os.path.relpath(path, formal)
        parts = relative.split(os.sep)
        seed = next((part for part in parts if part.startswith("seed_")), "")
        if seed in ("seed_2", "seed_3") and os.path.basename(path) in DETAIL_NAMES:
            excluded.append(path)
        else:
            included.add(path)
    return sorted(included), sorted(excluded)


def write_index(included, excluded):
    path = os.path.join(ROOT, "reports", "result_file_index.md")
    include_bytes = sum(os.path.getsize(item) for item in included
                        if os.path.isfile(item))
    exclude_bytes = sum(os.path.getsize(item) for item in excluded
                        if os.path.isfile(item))
    lines = ["# CBAP-v1 result file index", "",
             "- Included files: %d" % len(included),
             "- Included uncompressed bytes: %d" % include_bytes,
             "- Excluded seed-2/3 detailed trace files: %d" % len(excluded),
             "- Excluded trace bytes: %d" % exclude_bytes,
             "- All run summaries, manifests, results, configs, commands and "
             "all seed-1 packet/rate/control traces are retained.",
             "- Build objects, core dumps, unrelated experiments and old "
             "archives are excluded.", "", "## Exclusion rule", "",
             "For formal seed 2/3 only, packet traces, selected time series, "
             "sender TX events, per-epoch rate transitions and port summaries "
             "are omitted. Their run-level and per-flow summaries remain.",
             "", "## Included files", ""]
    lines.extend("- `%s` (%d bytes)" %
                 (os.path.relpath(item, REPO), os.path.getsize(item))
                 for item in included if os.path.isfile(item))
    lines.extend(["", "## Excluded detailed files", ""])
    lines.extend("- `%s` (%d bytes)" %
                 (os.path.relpath(item, REPO), os.path.getsize(item))
                 for item in excluded if os.path.isfile(item))
    with open(path, "w") as stream:
        stream.write("\n".join(lines) + "\n")
    return path


def main():
    prepare_metadata()
    included, excluded = select_files()
    index = write_index(included, excluded)
    included = sorted(set(included + [index]))
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive = os.path.join(REPO, "cbap_v1_fix_results_%s.tar.gz" % stamp)
    with tarfile.open(archive, "w:gz") as output:
        for path in included:
            output.add(path, arcname=os.path.relpath(path, REPO),
                       recursive=False)
    digest = hashlib.sha256()
    with open(archive, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    checksum = archive + ".sha256"
    with open(checksum, "w") as stream:
        stream.write("%s  %s\n" % (digest.hexdigest(),
                                    os.path.basename(archive)))
    # Verify every gzip/tar member is readable.
    with tarfile.open(archive, "r:gz") as source:
        member_count = len(source.getmembers())
    print("archive=%s" % archive)
    print("archive_size_bytes=%d" % os.path.getsize(archive))
    print("archive_members=%d" % member_count)
    print("sha256=%s" % checksum)


if __name__ == "__main__":
    main()
