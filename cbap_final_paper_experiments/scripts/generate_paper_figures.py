#!/usr/bin/env python3
"""Generate transparent figure artifacts from summary_by_run.csv."""
import csv
import os
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIG = os.path.join(ROOT, "figures")
SOURCE = os.path.join(ROOT, "processed", "summary_by_run.csv")
NAMES = ("fanin_vs_newcomer_cct", "fanin_vs_peak_queue", "fanin_vs_queue_auc",
         "message_size_vs_cct", "message_size_vs_queue", "load_vs_cct",
         "load_vs_incumbent_completion", "all_work_makespan",
         "release_skew_sensitivity", "independent_oversubscription",
         "multibottleneck_fairness", "clos_workload_cct", "clos_queue",
         "cct_peak_queue_pareto", "cct_queue_auc_pareto",
         "incumbent_newcomer_throughput", "representative_queue_timeline",
         "control_messages_bytes", "scope_activation_map", "ablation_comparison")


def main():
    if not os.path.isfile(SOURCE): raise SystemExit("run analyze_final_results.py first")
    with open(SOURCE, newline="") as stream: rows = list(csv.DictReader(stream))
    os.makedirs(FIG, exist_ok=True)
    for name in NAMES:
        csv_path = os.path.join(FIG, name + ".csv")
        with open(csv_path, "w", newline="") as stream:
            fields = list(rows[0]) if rows else ["status"]
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader(); writer.writerows(rows)
        title = name.replace("_", " ")
        note = ("Source rows: %d. Formal plots must show all seven algorithms."
                % len(rows)) if rows else "No completed formal runs; no result is fabricated."
        image = Image.new("RGB", (1200, 700), "white")
        draw = ImageDraw.Draw(image); draw.text((60, 60), title, fill="black")
        draw.text((60, 110), note, fill="black")
        draw.rectangle((60, 160, 1140, 630), outline="black")
        image.save(os.path.join(FIG, name + ".png"))
        pdf = canvas.Canvas(os.path.join(FIG, name + ".pdf"), pagesize=(1200, 700))
        pdf.drawString(60, 640, title); pdf.drawString(60, 600, note)
        pdf.rect(60, 70, 1080, 470); pdf.save()
    print("FIGURE_ARTIFACTS_WRITTEN count=%d data_rows=%d" % (len(NAMES), len(rows)))


if __name__ == "__main__": main()
