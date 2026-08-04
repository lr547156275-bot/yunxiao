#!/usr/bin/env bash
set -euo pipefail

V2_ROOT="$(cd "$(dirname "$0")" && pwd)"
SIM_ROOT="$(cd "$V2_ROOT/../.." && pwd)"
V1_ROOT="$V2_ROOT/../main_v1"
RERUN_MANIFEST="$V2_ROOT/config/rerun_manifest.csv"
RUN_ROOT="${RUN_ROOT:-$V2_ROOT/rerun_runs}"
JOBS="${JOBS:-1}"
MIN_FREE_GB="${MIN_FREE_GB:-5}"
KEEP_RAW="${KEEP_RAW:-0}"
RUN_TIMEOUT_MIN="${RUN_TIMEOUT_MIN:-60}"
FORCE_RERUN="${FORCE_RERUN:-1}"
export RUN_ROOT JOBS MIN_FREE_GB KEEP_RAW RUN_TIMEOUT_MIN FORCE_RERUN
export NS_LOG=""
ulimit -c 0

[[ -f "$RERUN_MANIFEST" ]] || {
  echo "REFUSE missing rerun manifest: $RERUN_MANIFEST" >&2
  exit 2
}
[[ "$JOBS" =~ ^[1-9][0-9]*$ ]] || {
  echo "REFUSE JOBS must be a positive integer" >&2
  exit 2
}
[[ "$RUN_TIMEOUT_MIN" =~ ^[1-9][0-9]*$ ]] || {
  echo "REFUSE RUN_TIMEOUT_MIN must be a positive integer" >&2
  exit 2
}

# Emit only manifest-authorized runs. Validation happens before common.sh is
# sourced, so an empty manifest exits without reaching any simulator launcher.
mapfile -t REQUIRED_ROWS < <(
  python3 - "$RERUN_MANIFEST" \
      "$V2_ROOT/config/main_manifest.csv" \
      "$V2_ROOT/config/reuse_manifest.csv" <<'PY'
import csv
import re
import sys

rerun_path, formal_path, reuse_path = sys.argv[1:]
required_fields = {
    "run_id", "scenario", "algorithm", "seed", "rerun_reason",
    "source_reuse_allowed",
}
with open(rerun_path, newline="") as stream:
    reader = csv.DictReader(stream)
    if set(reader.fieldnames or ()) != required_fields:
        raise SystemExit("rerun_manifest header mismatch")
    reruns = list(reader)
with open(formal_path, newline="") as stream:
    formal = {
        (row["scenario"], row["algorithm"], row["seed"]): row
        for row in csv.DictReader(stream)
    }
with open(reuse_path, newline="") as stream:
    reuse = {
        (row["scenario"], row["algorithm"], row["seed"]): row
        for row in csv.DictReader(stream)
    }

seen = set()
for row in reruns:
    key = (row["scenario"], row["algorithm"], row["seed"])
    if key in seen:
        raise SystemExit("duplicate rerun entry: " + "|".join(key))
    seen.add(key)
    if key not in formal:
        raise SystemExit("rerun is outside formal main-v2 manifest: " +
                         "|".join(key))
    expected_id = formal[key]["run_id"]
    if row["run_id"] != expected_id:
        raise SystemExit("run_id mismatch for " + "|".join(key))
    if not re.match(r"^[A-Za-z0-9_.-]+$", row["scenario"]) or \
            not re.match(r"^[A-Za-z0-9_.-]+$", row["algorithm"]) or \
            not re.match(r"^[1-9][0-9]*$", row["seed"]):
        raise SystemExit("unsafe manifest field in " + row["run_id"])
    if not row["rerun_reason"].strip():
        raise SystemExit("missing rerun_reason for " + row["run_id"])
    # Task 28 rule 1: a formally reusable run must never be rerun.
    source_allowed = row["source_reuse_allowed"].strip().lower()
    if source_allowed in {"1", "true", "yes"}:
        raise SystemExit("refuse reuse_allowed formal run: " + row["run_id"])
    if key in reuse and reuse[key]["reuse_allowed"].lower() == "true":
        raise SystemExit("refuse current reuse_manifest=true run: " +
                         row["run_id"])
    print(":".join(key))
PY
)

if (( ${#REQUIRED_ROWS[@]} == 0 )); then
  echo "NO_REQUIRED_RERUNS: rerun_manifest.csv contains only its header"
  exit 0
fi

# The existing runner prepares the same formal case, algorithm registration,
# seed, protocol configuration and output validation used by main-v1. RUN_ROOT
# is redirected to main-v2/rerun_runs, so no main-v1 result is overwritten.
TO_RUN=()
for item in "${REQUIRED_ROWS[@]}"; do
  IFS=: read -r scenario algorithm seed <<<"$item"
  run_dir="$RUN_ROOT/$scenario/$algorithm/seed_$seed"
  if [[ -f "$run_dir/completed.flag" ]] &&
      python3 "$V1_ROOT/scripts/check_main_outputs.py" reuse "$run_dir" \
        >/dev/null 2>&1; then
    echo "SKIP valid/hash-matched $scenario $algorithm seed=$seed"
  else
    TO_RUN+=("$item")
  fi
done

source "$V1_ROOT/scripts/common.sh"
if (( ${#TO_RUN[@]} > 0 )); then
  main_run_explicit "${TO_RUN[@]}"
fi

# Preserve provenance for later merge. This metadata is appended only after a
# run has completed and passed the original formal output checker.
python3 - "$RERUN_MANIFEST" "$V2_ROOT/config/reuse_manifest.csv" \
    "$RUN_ROOT" <<'PY'
import csv
import hashlib
import json
import os
import sys
import time

manifest_path, reuse_path, run_root = sys.argv[1:]
manifest_hash = hashlib.sha256(open(manifest_path, "rb").read()).hexdigest()
with open(manifest_path, newline="") as stream:
    reruns = list(csv.DictReader(stream))
with open(reuse_path, newline="") as stream:
    reuse = {
        (row["scenario"], row["algorithm"], row["seed"]): row
        for row in csv.DictReader(stream)
    }

index = []
for row in reruns:
    key = (row["scenario"], row["algorithm"], row["seed"])
    run_dir = os.path.join(run_root, row["scenario"], row["algorithm"],
                           "seed_" + row["seed"])
    meta_path = os.path.join(run_dir, "run_meta.json")
    completed = os.path.isfile(os.path.join(run_dir, "completed.flag"))
    status = "missing"
    if os.path.isfile(meta_path):
        with open(meta_path) as stream:
            meta = json.load(stream)
        status = "valid_completed" if completed and \
            int(meta.get("exit_status", -1)) == 0 else "incomplete_or_failed"
        source = reuse.get(key, {}).get(
            "source_run",
            "bop_exp/main_v1/runs/%s/%s/seed_%s" % key)
        meta.update({
            "result_source": "main_v2_required_rerun",
            "original_result_source": source,
            "rerun_reason": row["rerun_reason"],
            "rerun_manifest_sha256": manifest_hash,
            "source_reuse_allowed": False,
            "analysis_merge_policy":
                "replace_same_scenario_algorithm_seed_preserve_provenance",
            "provenance_updated_unix": time.time(),
        })
        temporary = meta_path + ".tmp"
        with open(temporary, "w") as stream:
            json.dump(meta, stream, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(temporary, meta_path)
    index.append({
        "run_id": row["run_id"],
        "scenario": row["scenario"],
        "algorithm": row["algorithm"],
        "seed": row["seed"],
        "result_source": "main_v2_required_rerun",
        "original_result_source": reuse.get(key, {}).get("source_run", ""),
        "rerun_reason": row["rerun_reason"],
        "status": status,
        "run_directory": os.path.relpath(run_dir, os.path.dirname(run_root)),
    })

os.makedirs(run_root, exist_ok=True)
index_path = os.path.join(run_root, "rerun_results_index.csv")
fields = [
    "run_id", "scenario", "algorithm", "seed", "result_source",
    "original_result_source", "rerun_reason", "status", "run_directory",
]
with open(index_path, "w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(index)
PY

echo "PASS required reruns=${#REQUIRED_ROWS[@]} output=$RUN_ROOT"
