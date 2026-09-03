#!/usr/bin/env python3
"""Nearest-rank p99 recalculation from raw flow_timing.csv (GPT round-2 item 3.2).

Rules (frozen metric definitions):
- completion start: application_ready_ns if > 0 (CBAP: includes 5us planning),
  else network_release_ns (baselines);
- completion end: last_ack_ns;
- population: synchronous batch flows only (background sender src=65 excluded);
  expected N: 32 for s5, 64 otherwise (warn, never silently drop);
- p99 nearest-rank: sorted[ceil(0.99*N)-1]  (N=64 -> the maximum).

Outputs /work/v2_stats/p99_nearest_rank_recalc.csv (+ changelog vs old
final_results_v2.csv when present).  Read-only on inputs.
"""
import csv, math, os, sys

ROOT = "/work/v2_400g/results"
OLD  = "/work/v2_400g/reports/final_results_v2.csv"
OUTD = "/work/v2_stats"
BG_SRC = "65"

def nearest_rank(vals, q):
    return vals[max(0, math.ceil(q * len(vals)) - 1)]

os.makedirs(OUTD, exist_ok=True)
rows, warns = [], []
for tag in sorted(os.listdir(ROOT)):
    ft = os.path.join(ROOT, tag, "flow_timing.csv")
    if not os.path.isfile(ft):
        continue
    comp = []
    with open(ft, newline="") as f:
        for r in csv.DictReader(f):
            if r["src"] == BG_SRC:
                continue
            ready = int(r["application_ready_ns"])
            start = ready if ready > 0 else int(r["network_release_ns"])
            end = int(r["last_ack_ns"])
            if end <= start:
                warns.append(f"{tag}: flow {r['flow_id']} non-positive completion")
                continue
            comp.append((end - start) / 1e6)  # ms
    if not comp:
        warns.append(f"{tag}: zero batch flows parsed"); continue
    exp = 32 if "_s5_" in tag or tag.endswith("_s5") else 64
    if len(comp) != exp:
        warns.append(f"{tag}: N={len(comp)} expected {exp}")
    comp.sort()
    rows.append({
        "tag": tag, "N": len(comp),
        "mean_ms": f"{sum(comp)/len(comp):.6f}",
        "p50_ms":  f"{nearest_rank(comp, 0.50):.6f}",
        "p95_ms":  f"{nearest_rank(comp, 0.95):.6f}",
        "p99_ms":  f"{nearest_rank(comp, 0.99):.6f}",
        "max_ms":  f"{comp[-1]:.6f}",
    })

old = {}
if os.path.isfile(OLD):
    with open(OLD, newline="") as f:
        for r in csv.DictReader(f):
            old[r["tag"]] = r.get("p99_cct_ms", "")

out = os.path.join(OUTD, "p99_nearest_rank_recalc.csv")
with open(out, "w", newline="") as f:
    fields = ["tag","N","mean_ms","p50_ms","p95_ms","p99_ms","max_ms",
              "old_p99_ms","delta_ms"]
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
    n_diff = 0
    for r in rows:
        o = old.get(r["tag"], "")
        r["old_p99_ms"] = o
        try:
            d = float(r["p99_ms"]) - float(o)
            r["delta_ms"] = f"{d:.6f}"
            if abs(d) > 1e-6: n_diff += 1
        except ValueError:
            r["delta_ms"] = ""
        w.writerow(r)

with open(os.path.join(OUTD, "P99_CHANGELOG.md"), "w") as f:
    f.write("# p99 nearest-rank recalc changelog\n\n")
    f.write(f"cells recalculated: {len(rows)}; cells with old value: "
            f"{sum(1 for r in rows if r['old_p99_ms'])}; "
            f"cells where p99 changed: {n_diff}\n\n")
    f.write("Note: N=64 nearest-rank p99 equals the batch maximum by "
            "definition (ceil(0.99*64)=64).\n\n## Warnings\n\n")
    for wmsg in warns: f.write(f"- {wmsg}\n")
    if not warns: f.write("- none\n")

print(f"recalc: {len(rows)} cells -> {out}")
print(f"warnings: {len(warns)} (see P99_CHANGELOG.md)")
print(f"p99 changed vs old: {n_diff} cells")
