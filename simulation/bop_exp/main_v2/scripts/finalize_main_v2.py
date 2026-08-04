#!/usr/bin/env python3
"""Finalize corrected main-v2 tables from existing results only.

This script is intentionally analysis-only.  It never invokes waf, changes a
simulation input, or mutates a main-v1 run.
"""
import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT.parents[1]
V1 = ROOT.parent / "main_v1"
OUT = ROOT / "analysis"
PAPER = SIM / "paper/experiments"
FORMAL_CC = ("dctcp", "dcqcn", "timely", "hpcc_int")
DISPLAY = {
    "dctcp": "DCTCP", "dcqcn": "DCQCN", "timely": "TIMELY",
    "hpcc_int": "HPCC-INT", "bop_qb": "BOP-QB",
}
LOWER = {"group_rct_mean_us", "queue_max_bytes", "queue_p95_bytes",
         "ecn_marks", "pfc_events", "completion_skew_us"}


def rows(path):
    with open(path, newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, fields, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(data)


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def change(new, baseline):
    if not math.isfinite(new) or not math.isfinite(baseline) or baseline == 0:
        return "NA"
    return (new - baseline) / baseline * 100.0


def fmt(value, digits=3):
    if isinstance(value, str):
        return value
    if not math.isfinite(value):
        return "NA"
    return ("%." + str(digits) + "f") % value


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    summary = rows(V1 / "analysis/scenario_summary.csv")
    lookup = {(r["scenario"], r["algorithm"], r["metric"]): number(r["mean"])
              for r in summary}
    specs = rows(ROOT / "config/main_scenarios.csv")
    spec = {r["scenario"]: r for r in specs}
    scenarios = [r["scenario"] for r in specs]

    best_rows = []
    pareto = []
    simultaneous = 0
    bounded_tradeoff = 0
    for scenario in scenarios:
        choices = [(lookup[(scenario, algorithm, "group_rct_mean_us")],
                    algorithm) for algorithm in FORMAL_CC]
        baseline_rct, baseline = min(choices)
        bop_rct = lookup[(scenario, "bop_qb", "group_rct_mean_us")]
        baseline_queue = lookup[(scenario, baseline, "queue_max_bytes")]
        bop_queue = lookup[(scenario, "bop_qb", "queue_max_bytes")]
        rct_change = change(bop_rct, baseline_rct)
        queue_change = change(bop_queue, baseline_queue)
        improves = rct_change < 0 and queue_change < 0
        bounded = rct_change <= 3 and queue_change <= -50
        simultaneous += int(improves)
        bounded_tradeoff += int(bounded)
        candidates = []
        for algorithm in FORMAL_CC + ("bop_qb",):
            candidates.append((
                lookup[(scenario, algorithm, "group_rct_mean_us")],
                lookup[(scenario, algorithm, "queue_max_bytes")],
                algorithm))
        bop_dominated = any(
            algorithm != "bop_qb" and rct <= bop_rct and queue <= bop_queue and
            (rct < bop_rct or queue < bop_queue)
            for rct, queue, algorithm in candidates)
        pareto.append({"scenario": scenario, "algorithm": "bop_qb",
                       "group_rct_mean_us": bop_rct,
                       "queue_max_bytes": bop_queue,
                       "pareto_optimal": str(not bop_dominated).lower(),
                       "comparison_set":
                       "dctcp|dcqcn|timely|hpcc_int|bop_qb"})
        best_rows.append({
            "scenario": scenario,
            "best_formal_cc_baseline": baseline,
            "best_formal_cc_rct_us": baseline_rct,
            "bop_qb_rct_us": bop_rct,
            "bop_qb_rct_change_pct": rct_change,
            "best_queue_max_bytes": baseline_queue,
            "bop_qb_queue_max_bytes": bop_queue,
            "queue_max_bytes_change_pct": queue_change,
            "best_queue_p95_bytes":
                lookup[(scenario, baseline, "queue_p95_bytes")],
            "bop_qb_queue_p95_bytes":
                lookup[(scenario, "bop_qb", "queue_p95_bytes")],
            "best_goodput_gbps":
                lookup[(scenario, baseline, "payload_goodput_gbps")],
            "bop_qb_goodput_gbps":
                lookup[(scenario, "bop_qb", "payload_goodput_gbps")],
            "goodput_change_pct": change(
                lookup[(scenario, "bop_qb", "payload_goodput_gbps")],
                lookup[(scenario, baseline, "payload_goodput_gbps")]),
            "best_ecn_marks": lookup[(scenario, baseline, "ecn_marks")],
            "bop_qb_ecn_marks": lookup[(scenario, "bop_qb", "ecn_marks")],
            "pfc_metric_status": "NA_RUNTIME_PATH_NOT_VERIFIED",
            "simultaneously_improves_rct_and_queue": int(improves),
            "rct_cost_le_3pct_queue_drop_ge_50pct": int(bounded),
            "bop_qb_pareto_optimal": int(not bop_dominated),
        })
    write_csv(OUT / "best_cc_baseline_comparison.csv",
              list(best_rows[0]), best_rows)
    write_csv(OUT / "pareto_points.csv", list(pareto[0]), pareto)

    pairwise = [r for r in rows(
        V1 / "analysis/pairwise_bop_vs_baselines.csv")
                if r["baseline_algorithm"] in FORMAL_CC]
    write_csv(OUT / "pairwise_bop_vs_cc.csv", list(pairwise[0]), pairwise)

    open_rows = []
    for scenario in scenarios:
        open_rct = lookup[(scenario, "pfc_only", "group_rct_mean_us")]
        bop_rct = lookup[(scenario, "bop_qb", "group_rct_mean_us")]
        open_queue = lookup[(scenario, "pfc_only", "queue_max_bytes")]
        bop_queue = lookup[(scenario, "bop_qb", "queue_max_bytes")]
        open_rows.append({
            "scenario": scenario,
            "reference_name": "open_loop_no_endhost_cc",
            "baseline_class": "open_loop_reference",
            "formal_cc_baseline": "false",
            "open_loop_rct_us": open_rct,
            "bop_qb_rct_us": bop_rct,
            "bop_qb_rct_cost_pct": change(bop_rct, open_rct),
            "open_loop_queue_max_bytes": open_queue,
            "bop_qb_queue_max_bytes": bop_queue,
            "bop_qb_queue_change_pct": change(bop_queue, open_queue),
            "open_loop_ecn_marks":
                lookup[(scenario, "pfc_only", "ecn_marks")],
            "pfc_events": "NA_UNVERIFIED",
            "pfc_pause_duration_us": "NA_UNVERIFIED",
            "buffer_occupancy_proxy": "queue_max_bytes",
            "semantic_caveat":
            "PFC configured but runtime pause behavior not verified",
        })
    write_csv(OUT / "open_loop_tradeoff.csv",
              list(open_rows[0]), open_rows)

    audit_expected = [
        ("msg_4m_n16_g50", "open_loop_pfc_configured"),
        ("msg_4m_n16_g50", "open_loop_pfc_disabled"),
        ("msg_64k_n16_g50", "open_loop_pfc_configured"),
        ("msg_64k_n16_g50", "open_loop_pfc_disabled"),
        ("msg_64k_n16_g50", "dcqcn"),
        ("msg_64k_n16_g50", "hpcc_int"),
        ("msg_64k_n16_g50", "bop_qb"),
        ("n64_64k_g50", "open_loop_pfc_configured"),
        ("n64_64k_g50", "open_loop_pfc_disabled"),
    ]
    audit_rows = []
    for scenario, algorithm in audit_expected:
        audit_rows.append({
            "scenario": scenario, "algorithm": algorithm, "seed": 1,
            "audit_status": "NOT_RUN",
            "queue_object_id": "", "pfc_queue_object_id": "",
            "queue_max_bytes": "", "pfc_threshold_bytes": "",
            "pause_generated_count": "", "pause_received_count": "",
            "pause_duration_us": "", "pfc_path_verified": "",
            "primary_pfc_conclusion": "OPEN_LOOP_NOT_PFC_BASELINE",
            "evidence":
            "event-level audit output absent; historical counter cannot verify runtime pause path",
        })
    write_csv(OUT / "pfc_semantic_audit.csv",
              list(audit_rows[0]), audit_rows)

    current_n32 = lookup[("n32_64k_g50", "dcqcn",
                          "group_rct_mean_us")]
    legacy_n32 = 213.184
    dcqcn_rows = [{
        "comparison": "legacy_final_validation_vs_current_main_v1",
        "legacy_mean_rct_us": legacy_n32,
        "current_mean_rct_us": current_n32,
        "difference_us": current_n32 - legacy_n32,
        "relative_change_pct": change(current_n32, legacy_n32),
        "current_three_seed_hash_status": "VALID_REUSE",
        "current_seed1_replay_status": "NOT_RUN",
        "legacy_config_unavailable": "true",
        "dcqcn_conclusion": "DCQCN_DRIFT_UNRESOLVED",
        "reason":
        "legacy topology/config/flow/round/fixed-path inputs were not retained",
    }]
    write_csv(OUT / "dcqcn_n32_reproducibility.csv",
              list(dcqcn_rows[0]), dcqcn_rows)

    reuse = rows(ROOT / "config/reuse_manifest.csv")
    allowed = sum(r["reuse_allowed"] == "true" for r in reuse)
    section_counts = {
        section: sum(r["section"] == section for r in reuse)
        for section in ("main", "ablation", "wire_fairness")
    }
    reuse_rows = [{
        "expected_formal_runs": 273,
        "main_runs": section_counts["main"],
        "ablation_runs": section_counts["ablation"],
        "wire_fairness_runs": section_counts["wire_fairness"],
        "reuse_allowed_runs": allowed,
        "reuse_rejected_runs": len(reuse) - allowed,
        "open_loop_historical_runs": 45,
        "semantic_audit_expected_runs": 9,
        "semantic_audit_completed_runs": 0,
        "formal_rerun_count": 0,
        "main_v1_results_modified": "false",
    }]
    write_csv(OUT / "reuse_summary.csv", list(reuse_rows[0]), reuse_rows)
    write_csv(OUT / "invalid_runs.csv",
              ["run_id", "scenario", "algorithm", "seed", "reason"], [])
    # Rule 1 of task 28 forbids rerunning all 273 reuse-allowed runs.  The
    # historical configuration loss cannot be repaired by repeating current
    # inputs, so the minimum simulation rerun list is empty.
    write_csv(ROOT / "config/rerun_manifest.csv",
              ["run_id", "scenario", "algorithm", "seed",
               "rerun_reason", "source_reuse_allowed"], [])

    scan_groups = [
        ("Message size", "message_size"),
        ("Participants", "participants"),
        ("Compute gap", "compute_gap"),
        ("Heterogeneity", "heterogeneity"),
    ]
    report = [
        "# Corrected BOP-QB main-v2 report",
        "",
        "## 唯一判定：`DCQCN_REVIEW_REQUIRED`",
        "",
        "正式 273 次运行的哈希与配置复用审计为 273/273 通过，但该判定"
        "不能升级为 MAIN_V2_READY：旧 final-validation 的 n32 DCQCN "
        "原始输入未保留，当前 %.3f us 与旧报告 %.3f us 的漂移无法解释。"
        % (current_n32, legacy_n32),
        "",
        "PFC 主结论为 `OPEN_LOOP_NOT_PFC_BASELINE`。历史模式统一称为 "
        "`open_loop_no_endhost_cc`；PFC configured but runtime pause behavior "
        "not verified。它不属于正式 CC 基线，也不进入主胜负统计。",
        "",
        "## 完整性与最小重跑",
        "",
        "- 正式语料：225 主实验 + 30 消融 + 18 wire fairness = 273。",
        "- `reuse_allowed=true`：273/273；Open-loop 历史结果 45 次另表。",
        "- main-v2 事件级语义审计完成 0/9，缺失事件没有补成 0。",
        "- `rerun_manifest.csv` 只有表头。当前正式运行均可复用；再次运行"
        "当前 n32 配置不能恢复缺失的旧配置或解释跨版本漂移。",
        "- 需要的最小非仿真工作是找回旧 topology/config/flow/round/"
        "fixed-path/run_meta，或独立审查为何旧归档未保留它们。",
        "",
        "## 正式比较口径",
        "",
        "正式基线仅包括 DCTCP、DCQCN、TIMELY、HPCC-INT。每个场景的 "
        "best formal CC baseline 是其中 mean group RCT 最低者。Open-loop、"
        "Wire-Equalized DCQCN、Gate 与 BOP 均不参与该选择。",
        "",
        "## BOP-QB 与 best formal CC baseline",
        "",
        "| 场景 | 正式基线 | 基线 RCT us | BOP-QB RCT us | RCT变化 | "
        "queue变化 | Pareto |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in best_rows:
        report.append("| %s | %s | %s | %s | %s%% | %s%% | %s |" % (
            row["scenario"], DISPLAY[row["best_formal_cc_baseline"]],
            fmt(row["best_formal_cc_rct_us"]),
            fmt(row["bop_qb_rct_us"]),
            fmt(row["bop_qb_rct_change_pct"], 2),
            fmt(row["queue_max_bytes_change_pct"], 2),
            "yes" if row["bop_qb_pareto_optimal"] else "no"))
    report += [
        "",
        "BOP-QB 同时改善 RCT 与峰值队列的场景为 **%d/15**；以不超过 "
        "3%% RCT 代价换取至少 50%% 峰值队列下降的场景为 **%d/15**。"
        % (simultaneous, bounded_tradeoff),
        "这替代旧报告错误地以 Open-loop 作为最佳基线所得的 0/15 "
        "结论。",
        "",
        "## 四类扫描",
        "",
    ]
    for title, sweep in scan_groups:
        report += ["### " + title, "",
                   "| 场景 | BOP-QB RCT us | 相对正式最佳RCT变化 | "
                   "相对正式最佳queue变化 |",
                   "|---|---:|---:|---:|"]
        for row in best_rows:
            in_scan = spec[row["scenario"]]["sweep"] == sweep
            if sweep == "compute_gap" and \
                    row["scenario"] == "msg_64k_n16_g50":
                in_scan = True
            if in_scan:
                report.append("| %s | %s | %s%% | %s%% |" % (
                    row["scenario"], fmt(row["bop_qb_rct_us"]),
                    fmt(row["bop_qb_rct_change_pct"], 2),
                    fmt(row["queue_max_bytes_change_pct"], 2)))
        report.append("")
    ablation = rows(V1 / "analysis/ablation.csv")
    report += [
        "## Gate → BOP → BOP-QB 消融",
        "",
        "| 场景 | 比较 | RCT变化 | queue变化 | goodput变化 |",
        "|---|---|---:|---:|---:|",
    ]
    for row in ablation:
        report.append("| %s | %s | %s%% | %s%% | %s%% |" % (
            row["scenario"], row["comparison"],
            fmt(number(row["group_rct_change_pct"]), 2),
            fmt(number(row["queue_max_change_pct"]), 2),
            fmt(number(row["goodput_change_pct"]), 2)))
    wire = rows(V1 / "analysis/wire_fairness.csv")
    report += [
        "",
        "## Wire-Equalized 公平性",
        "",
        "该模式仅为诊断，不是正式基线。既有结果保持不变：",
        "",
        "| 场景 | 每DATA额外字节 | RCT差距解释比例 | BOP-QB对Equalized RCT | "
        "BOP-QB对Equalized queue |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in wire:
        report.append("| %s | %s | %s | %s%% | %s%% |" % (
            row["scenario"], row["mean_wire_bytes_difference"],
            row["wire_bytes_explained_rct_gap_pct"],
            fmt(number(row["bop_vs_equalized_rct_pct"]), 2),
            fmt(number(row["bop_vs_equalized_queue_pct"]), 2)))
    report += [
        "",
        "## PFC 与 Open-loop 处理",
        "",
        "- 主结论：`OPEN_LOOP_NOT_PFC_BASELINE`。",
        "- 事件级审计 0/9；历史 PFC 数字在本报告中标记 NA，不声明 "
        "BOP-QB 改善 PFC。",
        "- Open-loop 仅在 `open_loop_tradeoff.csv` 和附录使用。",
        "",
        "## DCQCN 跨版本审计",
        "",
        "- 结论：`DCQCN_DRIFT_UNRESOLVED`。",
        "- 当前 main-v1 n32 DCQCN 三-seed mean RCT：%.3f us；旧报告："
        "%.3f us；差值 %.3f us（%.2f%%）。"
        % (current_n32, legacy_n32, current_n32 - legacy_n32,
           change(current_n32, legacy_n32)),
        "- 当前 273 次正式运行并未因此被判定为哈希无效，但在解释该"
        "漂移前不能完成正式论文结论。",
        "",
        "## 不能得出的结论",
        "",
        "- 不能称 Open-loop 为 PFC-only 正式基线。",
        "- 不能从旧的零计数宣称 PFC 未触发或 BOP-QB 降低 PFC。",
        "- 不能用三 seed 外推生产网络、动态路由或多瓶颈。",
        "- 不能解释 n32 DCQCN 的跨版本漂移，直到旧输入证据恢复。",
        "",
    ]
    (OUT / "corrected_main_report.md").write_text(
        "\n".join(report), encoding="utf-8")

    (OUT / "suspicious_findings.md").write_text(
        "# Suspicious findings\n\n"
        "1. `main_v2/audit_runs` is empty: the required nine event-level PFC "
        "audits were not run. Missing counters remain NA.\n"
        "2. Historical queue statistics and PFC decisions use different "
        "accounting objects, so old zero PFC counts do not verify semantics.\n"
        "3. n32 DCQCN differs by %.3f us (+%.2f%%) from the archived report; "
        "the archive lacks the raw legacy inputs.\n"
        "4. All 273 current formal entries pass reuse validation. Their "
        "rerun is forbidden by the task and would not recover legacy evidence."
        "\n" % (current_n32 - legacy_n32,
                 change(current_n32, legacy_n32)),
        encoding="utf-8")

    paper = [
        "# 第5章 实验评估（main-v2 修正版）",
        "",
        "## 当前判定",
        "",
        "**DCQCN_REVIEW_REQUIRED**。273 个正式运行均通过复用审计，但 "
        "n32 DCQCN 跨版本漂移尚未解释。本章数字可作为审计中的仿真"
        "结果，不能作为已经最终冻结的论文结论。",
        "",
        "## 实验口径",
        "",
        "结果来自 ns-3 固定 ECMP、100 Gbit/s 单共享瓶颈仿真。正式基线"
        "仅为 DCTCP、DCQCN、TIMELY 和 HPCC-INT。BOP-QB 分别与四者"
        "比较；best formal CC baseline 只从四者按 mean group RCT 选择。",
        "",
        "历史 `pfc_only` 统一改称 `open_loop_no_endhost_cc`，仅作为"
        " uncontrolled injection reference。PFC configured but runtime "
        "pause behavior not verified。它不参与主胜负统计。",
        "",
        "## 修正后的主结果",
        "",
        "相对 best formal CC baseline，BOP-QB 在 %d/15 场景同时改善 RCT "
        "和峰值队列；在 %d/15 场景以不超过 3%% RCT 代价换取至少 "
        "50%% 峰值队列下降。完整逐场景数字见 "
        "`bop_exp/main_v2/analysis/best_cc_baseline_comparison.csv`。"
        % (simultaneous, bounded_tradeoff),
        "",
        "消息大小、参与者、compute gap 和异构性扫描均保留所有场景。"
        "Gate→BOP→BOP-QB 消融与 Wire-Equalized 诊断复用既有数据；"
        "Wire-Equalized 不替代标准 DCQCN。",
        "",
        "## PFC 与重现性限制",
        "",
        "main-v2 的九次事件级 PFC 审计尚未执行，因此 PFC 指标标记 NA，"
        "不声明 BOP-QB 改善 PFC。n32 DCQCN 当前均值 %.3f us，旧报告 "
        "%.3f us；旧原始输入缺失，结论为 DCQCN_DRIFT_UNRESOLVED。"
        % (current_n32, legacy_n32),
        "",
        "## 适用边界",
        "",
        "三 seed 只反映当前有限输入；结果不代表真实 GPU/NCCL、生产"
        "部署、动态路由、多瓶颈或强背景流。",
        "",
    ]
    (PAPER / "chapter_5_experiments_results.md").write_text(
        "\n".join(paper), encoding="utf-8")

    tables = [
        "# Chapter 5 corrected main-v2 result tables",
        "",
        "Open-loop is excluded. Best baseline means best formal CC baseline.",
        "",
        "| Scenario | Best formal CC | Baseline RCT us | BOP-QB RCT us | "
        "RCT change % | Queue change % |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in best_rows:
        tables.append("| %s | %s | %s | %s | %s | %s |" % (
            row["scenario"], DISPLAY[row["best_formal_cc_baseline"]],
            fmt(row["best_formal_cc_rct_us"], 2),
            fmt(row["bop_qb_rct_us"], 2),
            fmt(row["bop_qb_rct_change_pct"], 2),
            fmt(row["queue_max_bytes_change_pct"], 2)))
    tables += [
        "",
        "Simultaneous RCT+queue improvements: %d/15." % simultaneous,
        "RCT cost <=3%% with queue reduction >=50%%: %d/15."
        % bounded_tradeoff,
        "PFC metrics: NA pending event-level audit.",
    ]
    (PAPER / "main_result_tables.md").write_text(
        "\n".join(tables), encoding="utf-8")

    claims = [
        {"claim_id": "C1", "research_question": "RQ1",
         "status": "supported_in_subset",
         "evidence": "%d/15 simultaneous RCT+queue improvements versus best formal CC baseline" % simultaneous,
         "limitation": "DCQCN n32 drift unresolved"},
        {"claim_id": "C2", "research_question": "RQ2",
         "status": "supported_in_subset",
         "evidence": "%d/15 scenarios meet <=3%% RCT cost and >=50%% queue reduction" % bounded_tradeoff,
         "limitation": "fixed single bottleneck; three seeds"},
        {"claim_id": "C3", "research_question": "RQ3",
         "status": "qualified_by_scans",
         "evidence": "message-size, participant, gap and heterogeneity scans",
         "limitation": "n<=64; ns-3 only"},
        {"claim_id": "C4", "research_question": "RQ4",
         "status": "supported_by_ablation",
         "evidence": "Gate->BOP->BOP-QB in five scenarios",
         "limitation": "ablation is not an external baseline"},
        {"claim_id": "C5", "research_question": "RQ5",
         "status": "diagnostic_only",
         "evidence": "Wire-Equalized DCQCN comparison",
         "limitation": "not a production baseline"},
        {"claim_id": "C6", "research_question": "PFC semantics",
         "status": "not_supported",
         "evidence": "OPEN_LOOP_NOT_PFC_BASELINE; event audit 0/9",
         "limitation": "PFC metrics NA"},
        {"claim_id": "C7", "research_question": "DCQCN reproducibility",
         "status": "review_required",
         "evidence": "262.024 us current versus 213.184 us archived",
         "limitation": "legacy raw inputs unavailable"},
    ]
    write_csv(PAPER / "claims_registry_filled.csv",
              ["claim_id", "research_question", "status", "evidence",
               "limitation"], claims)
    print("judgement=DCQCN_REVIEW_REQUIRED formal_reuse=%d reruns=0 "
          "simultaneous=%d bounded_tradeoff=%d" %
          (allowed, simultaneous, bounded_tradeoff))


if __name__ == "__main__":
    main()
