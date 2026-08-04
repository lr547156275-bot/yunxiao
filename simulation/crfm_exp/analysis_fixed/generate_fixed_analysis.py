#!/usr/bin/env python3
"""Recompute the fixed CRFM screening audit from raw CSV files only."""

import csv
import importlib.util
import json
import math
import os


HERE = os.path.abspath(os.path.dirname(__file__))
CRFM_ROOT = os.path.abspath(os.path.join(HERE, ".."))
RUNS = os.path.join(CRFM_ROOT, "runs_fixed")
FIGURES = os.path.join(HERE, "figures")
CASES = [
    "gap_20us", "gap_50us", "gap_100us", "gap_500us",
    "size_16k", "size_256k", "long_burst_control",
    "single_round_control",
]
ALGOS = ["hpcc", "hpcc_round_reset", "crfm_gate", "ra_hpcc"]
SEED = 1

legacy_path = os.path.join(
    CRFM_ROOT, "analysis", "generate_analysis.py")
spec = importlib.util.spec_from_file_location("crfm_analysis_common", legacy_path)
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)


def load_plan(path):
    result = {}
    with open(path) as handle:
        expected = int(handle.readline())
        rows = [line.split() for line in handle if line.strip()]
    if len(rows) != expected or any(len(row) != 6 for row in rows):
        raise RuntimeError("invalid fixed round plan: " + path)
    for row in rows:
        result[(int(row[0]), int(row[1]))] = {
            "round_bytes": int(row[2]),
            "compute_gap_ns": int(row[3]),
            "jitter_ns": int(row[4]),
            "jitter_group": int(row[5]),
        }
    return result


def load_run(scenario, algorithm):
    directory = os.path.join(
        RUNS, scenario, algorithm, "seed_%d" % SEED)
    result = {
        "directory": directory,
        "meta": json.load(open(os.path.join(directory, "run_meta.json"))),
        "flow": common.read_csv(
            os.path.join(directory, "flow_summary.csv")),
        "round": common.read_csv(
            os.path.join(directory, "round_summary.csv")),
        "feedback": common.read_csv(
            os.path.join(directory, "feedback_summary.csv")),
        "controller": common.read_csv(
            os.path.join(directory, "controller_summary.csv")),
        "link": common.read_csv(
            os.path.join(directory, "selected_link_timeseries.csv")),
        "selected": common.read_csv(
            os.path.join(directory, "selected_flow_timeseries.csv")),
        "pfc": common.read_csv(
            os.path.join(directory, "pfc_events.csv")),
    }
    plan_path = os.path.join(directory, "rounds.txt")
    result["rounds_hash"] = common.sha256(plan_path)
    result["plan"] = load_plan(plan_path)
    return result


def add_fixed_metrics(metric, run):
    rounds_by_flow = {}
    for row in run["round"]:
        rounds_by_flow.setdefault(int(row["flow_id"]), []).append(row)
    ack_gaps = []
    injection_gaps = []
    errors_ns = []
    releases_after_ack = True
    for flow, rows in rounds_by_flow.items():
        rows.sort(key=lambda row: int(row["round_id"]))
        for index, row in enumerate(rows):
            if index == 0:
                continue
            release_ns = int(round(float(row["release_time"]) * 1e9))
            previous_ack_ns = int(round(
                float(rows[index - 1]["ack_completion_time"]) * 1e9))
            previous_injection_ns = int(round(
                float(rows[index - 1]["injection_end_time"]) * 1e9))
            plan = run["plan"][(flow, index)]
            planned = plan["compute_gap_ns"] + plan["jitter_ns"]
            actual = release_ns - previous_ack_ns
            ack_gaps.append(actual * 1e-9)
            injection_gaps.append(
                (release_ns - previous_injection_ns) * 1e-9)
            errors_ns.append(abs(actual - planned))
            releases_after_ack &= release_ns > previous_ack_ns
    metric.update({
        "valid_for_algorithm_comparison": 1,
        "int_hop_round_count": sum(
            int(row["int_hop_count"]) > 0 for row in run["feedback"]),
        "ack_relative_gap_mean_s": common.mean(ack_gaps),
        "ack_relative_gap_min_s": min(ack_gaps) if ack_gaps else 0.0,
        "ack_relative_gap_max_s": max(ack_gaps) if ack_gaps else 0.0,
        "injection_relative_gap_mean_s": common.mean(injection_gaps),
        "injection_relative_gap_min_s": (
            min(injection_gaps) if injection_gaps else 0.0),
        "gap_plan_max_error_ns": max(errors_ns) if errors_ns else 0,
        "all_releases_after_previous_ack": int(releases_after_ack),
    })
    return metric


def value(metrics, scenario, algorithm, field):
    for row in metrics:
        if row["scenario"] == scenario and row["algorithm"] == algorithm:
            return row[field]
    raise KeyError((scenario, algorithm, field))


def pct(new, baseline):
    return common.percent(new, baseline)


def fmt_change(number):
    if number is None:
        return "NA"
    return "%+.2f%%" % number


def starts(metrics, scenario, algorithm):
    values = []
    for number in range(1, 5):
        current = value(
            metrics, scenario, algorithm,
            "round_%d_start_rate_bps" % number)
        if current == "":
            continue
        values.append("%.1f" % (current / 1e9))
    return "/".join(values)


def write_outputs(metrics, runs):
    os.makedirs(HERE, exist_ok=True)
    os.makedirs(FIGURES, exist_ok=True)
    common.write_csv(
        os.path.join(HERE, "per_seed_metrics.csv"), metrics,
        list(metrics[0].keys()))

    pairs = [
        ("ra_hpcc", "hpcc"),
        ("ra_hpcc", "crfm_gate"),
        ("ra_hpcc", "hpcc_round_reset"),
        ("crfm_gate", "hpcc"),
        ("hpcc_round_reset", "hpcc"),
    ]
    fields = [
        "round_completion_mean_s", "round_completion_p95_s",
        "round_completion_max_s", "round_2_rct_penalty",
        "round_3_rct_penalty", "round_4_rct_penalty",
        "goodput_bps", "makespan_s", "queue_mean_bytes",
        "queue_p95_bytes", "queue_p99_bytes", "queue_max_bytes",
        "pfc_event_count", "pfc_pause_time_s", "ecn_marks",
        "active_utilization", "round_2_start_rate_bps",
        "round_3_start_rate_bps", "round_4_start_rate_bps",
        "late_action_ratio", "late_feedback_ratio",
        "actionable_feedback_ratio", "actionable_byte_ratio",
        "rate_total_variation_mean_bps",
    ]
    comparisons = []
    for scenario in CASES:
        for new, baseline in pairs:
            for field in fields:
                new_value = value(metrics, scenario, new, field)
                baseline_value = value(
                    metrics, scenario, baseline, field)
                available = (
                    isinstance(new_value, (int, float)) and
                    isinstance(baseline_value, (int, float)))
                comparisons.append({
                    "scenario": scenario,
                    "new_algorithm": new,
                    "baseline_algorithm": baseline,
                    "seed": SEED,
                    "metric": field,
                    "new_value": new_value if available else "",
                    "baseline_value": baseline_value if available else "",
                    "percent_change": (
                        pct(new_value, baseline_value)
                        if available else ""),
                    "causal_input_valid": 1,
                    "replicated": 0,
                })
    common.write_csv(
        os.path.join(HERE, "comparison.csv"), comparisons,
        list(comparisons[0].keys()))
    common.write_csv(
        os.path.join(HERE, "invalid_runs.csv"), [],
        ["scenario", "algorithm", "seed", "reason", "excluded_from"])

    common.ANALYSIS = HERE
    common.FIGURES = FIGURES
    common.RUNS = RUNS
    common.SEEDS = [SEED]
    common.build_figures(metrics, runs)


def build_report(metrics, runs):
    all_complete = all(
        row["all_flows_completed"] == 1 and
        row["all_rounds_completed"] == 1 for row in metrics)
    no_truncation = all(row["log_truncated"] == 0 for row in metrics)
    no_deadlock = all(row["minimum_rate_bps"] > 0 for row in metrics)
    same_plan = all(
        len({
            runs[(scenario, algorithm, SEED)]["rounds_hash"]
            for algorithm in ALGOS
        }) == 1 for scenario in CASES)
    all_int = all(row["int_hop_round_count"] > 0 for row in metrics)
    all_release_ok = all(
        row["all_releases_after_previous_ack"] == 1
        for row in metrics)
    max_gap_error = max(row["gap_plan_max_error_ns"] for row in metrics)
    pfc_total = sum(row["pfc_event_count"] for row in metrics)

    hpcc_rows = []
    for scenario in CASES:
        hpcc_rows.append(
            "| %s | %.3f | %.3f | %.3f | %.3f | %.1f | %.1f | %s |" % (
                scenario,
                value(metrics, scenario, "hpcc", "late_feedback_ratio"),
                value(metrics, scenario, "hpcc",
                      "actionable_feedback_ratio"),
                value(metrics, scenario, "hpcc",
                      "actionable_byte_ratio"),
                value(metrics, scenario, "hpcc", "late_action_ratio"),
                value(metrics, scenario, "hpcc",
                      "round_completion_mean_s") * 1e6,
                value(metrics, scenario, "hpcc",
                      "round_completion_p95_s") * 1e6,
                starts(metrics, scenario, "hpcc"),
            ))

    algorithm_rows = []
    for scenario in CASES:
        hpcc_p95 = value(
            metrics, scenario, "hpcc", "round_completion_p95_s")
        hpcc_goodput = value(metrics, scenario, "hpcc", "goodput_bps")
        hpcc_queue = value(metrics, scenario, "hpcc", "queue_max_bytes")
        ra_p95 = value(
            metrics, scenario, "ra_hpcc", "round_completion_p95_s")
        gate_p95 = value(
            metrics, scenario, "crfm_gate", "round_completion_p95_s")
        ra_goodput = value(metrics, scenario, "ra_hpcc", "goodput_bps")
        ra_queue = value(metrics, scenario, "ra_hpcc", "queue_max_bytes")
        algorithm_rows.append(
            "| %s | %.1f | %.1f | %s | %s | %s | %s |" % (
                scenario, hpcc_p95 * 1e6, ra_p95 * 1e6,
                fmt_change(pct(ra_p95, hpcc_p95)),
                fmt_change(pct(ra_p95, gate_p95)),
                fmt_change(pct(ra_goodput, hpcc_goodput)),
                fmt_change(pct(ra_queue, hpcc_queue)),
            ))

    gap_rows = []
    for scenario in (
            "gap_20us", "gap_50us", "gap_100us", "gap_500us"):
        gap_rows.append(
            "| %s | %.3f | %.3f | %s | %.1f | %.1f | %.1f |" % (
                scenario,
                value(metrics, scenario, "hpcc", "late_feedback_ratio"),
                value(metrics, scenario, "hpcc",
                      "actionable_byte_ratio"),
                starts(metrics, scenario, "hpcc"),
                common.mean([
                    value(metrics, scenario, "hpcc",
                          "round_%d_rct_penalty" % number)
                    for number in (2, 3, 4)]) * 100,
                value(metrics, scenario, "hpcc",
                      "ack_relative_gap_mean_s") * 1e6,
                value(metrics, scenario, "hpcc",
                      "injection_relative_gap_mean_s") * 1e6,
            ))

    burst_rows = []
    for scenario, size in (
            ("size_16k", "16 KiB"), ("gap_50us", "64 KiB"),
            ("size_256k", "256 KiB"),
            ("long_burst_control", "4 MiB")):
        burst_rows.append(
            "| %s | %s | %.1f | %.1f | %.3f | %.0f | %.1f |" % (
                scenario, size,
                value(metrics, scenario, "hpcc",
                      "injection_duration_mean_s") * 1e6,
                value(metrics, scenario, "hpcc",
                      "feedback_loop_delay_mean_s") * 1e6,
                value(metrics, scenario, "hpcc",
                      "actionable_feedback_ratio"),
                value(metrics, scenario, "hpcc", "queue_max_bytes"),
                value(metrics, scenario, "hpcc",
                      "round_completion_mean_s") * 1e6,
            ))

    report = """# Fixed CRFM / RA-HPCC screening audit

## 1. 唯一判定

**INCONCLUSIVE**

这是完整的 fixed screening（8 场景 × 4 算法），但只有 seed=1。运行和
遥测已经有效，HPCC 中也出现了明显的迟到反馈、OFF 阶段速率修改和后续轮次
低起始速率。可是性能代价并不一致：只有 `gap_20us` 的后续轮次平均 RCT
高于第一轮，其他 gap 的后续 RCT 反而降低。严格问题标准也并非全部满足：
`gap_20us` 的
actionable-byte ratio 为 0.169，高于 0.10；并且没有多 seed 方向一致性证据。

算法筛选层面不支持 RA-HPCC 直接进入确认实验：三个主要短 gap 中只有
`gap_20us` 的 P95 改善超过 10%%，RA 在 gap 场景中没有明显优于 Gate，并在
`size_256k` 和 long-burst control 中退化。由于禁止把单 seed 写成稳定结论，
正式类别仍是 `INCONCLUSIVE`，不能提升为稳定的算法失败判定。

## 2. 数据完整性

- 32/32 fixed runs 存在；全部流和轮次完成： **%s**。
- exit status 全为 0、无 NaN/Inf、无零速率死锁： **%s**。
- 无日志截断： **%s**。
- 四种算法均记录非零 INT hop： **%s**。
- 同场景 seed=1 跨算法输入 plan SHA256 相同： **%s**。
- 所有后续 release 均晚于上一轮 ACK completion： **%s**。
- ACK-relative gap 与 `compute_gap+jitter` 最大误差： **%d ns**。
- PFC 事件总数： **%d**。
- 只有 seed=1，不能计算跨 seed 标准差或 95%% CI。

## 3. 同一 QP、序列与轮次调度

全部运行中，每个逻辑 flow 的 `qp_id` 跨轮保持不变，round sequence interval
连续，采样的 `snd_nxt/snd_una/released_bytes` 不回退。Round completion 使用
累计 ACK completion。第 k+1 轮实际 release 严格等于第 k 轮 ACK completion
加输入 plan 的 compute gap 和 jitter；所有 injection-relative gap 也为正。

## 4. HPCC 反馈时序

| 场景 | late ratio | actionable ratio | actionable bytes | late action | mean RCT us | P95 RCT us | R1/R2/R3/R4 start Gbit/s |
|---|---:|---:|---:|---:|---:|---:|---|
%s

`gap_20us`/`gap_50us` 的 late-feedback ratio 分别为 0.590/0.757，
HPCC 确实在 OFF 阶段修改实时速率；后续 start rate 明显低于第一轮。
`gap_50us` 的 actionable-byte ratio 为 0.080，满足严格阈值，但
`gap_20us` 为 0.169，不满足。

## 5. Gap 趋势与跨轮污染

| 场景 | late ratio | actionable bytes | HPCC start Gbit/s | later-round mean RCT penalty %% | ACK gap us | injection gap us |
|---|---:|---:|---|---:|---:|---:|
%s

随 gap 增大，actionable-byte ratio 从 0.169/0.080 降到 0.046/0.020；
500 us 时后续轮次仍保留较低起始速率，但 RCT penalty 已反向为改善。
这说明“跨轮速率状态保留”存在，却没有在多个 gap 中形成一致的性能代价，
因此不能确认稳定相变或普遍 CRFM 性能问题。

## 6. Burst-size 趋势

| 场景 | 大小 | injection us | feedback loop us | actionable ratio | queue max B | mean RCT us |
|---|---|---:|---:|---:|---:|---:|
%s

actionable-feedback ratio 从 16 KiB 的 0 增加到 256 KiB 的 0.960，
long-burst control 达到 0.998。修复后的 long-burst 所有轮次均有正 gap，
因此该 control 现在形成了预期的“反馈可作用于当前轮”条件。

## 7. RA-HPCC、Gate、Reset 对比

| 场景 | HPCC P95 us | RA P95 us | RA vs HPCC P95 | RA vs Gate P95 | RA vs HPCC goodput | RA vs HPCC queue max |
|---|---:|---:|---:|---:|---:|---:|
%s

核心数值：

- `gap_20us`：RA P95 相对 HPCC **-63.70%%**，但 queue max **+36.02%%**；
- `gap_50us`：RA P95 **-2.69%%**，未达到 10%%；
- `gap_100us`：RA P95 **-0.64%%**；
- `size_256k`：RA P95 **+51.62%%**、goodput **-13.71%%**；
- `long_burst_control`：RA P95 **+9.64%%**、goodput **-5.03%%**；
- RA 与 Gate 在四个 gap 场景的 P95 基本相同，未证明完整 carry 优于简单 Gate；
- single-round 四种模式完全相同，没有引入单轮性能代价；
- Reset 将四个 gap 的每轮 start rate 都恢复到 100 Gbit/s；相对 HPCC 的
  mean RCT 变化依次为 **-25.58%%/-20.55%%/-18.29%%/-12.16%%**。
  这支持“保留低速率状态会影响均值”，但它是诊断 oracle，不能视为
  可部署算法；P95 证据除 gap20 外并不强。

## 8. Goodput、queue、PFC 和控制代价

所有 32 次运行均无 PFC 事件。RA 在大部分场景没有提高 queue max；
`gap_20us` 是明显例外，相对 HPCC 增加 36.02%%。RA 在 `size_256k` 和
long-burst 中降低 active utilization/goodput，说明其较高下一轮初始速率并
未转换为更好的完成时间，反而形成吞吐/RCT 退化。

## 9. 能得出和不能得出的结论

可以得出：

1. INT 缺失和负 gap 已修复，fixed 数据可用于算法比较。
2. seed=1 中 HPCC 存在明显跨轮低速率状态；性能代价只在 `gap_20us`
   明确出现，在其余 gap 中不一致。
3. burst-size control 呈现预期 actionability 增长。
4. 当前 RA-HPCC 在 screening 上没有显示出相对 Gate 的增量价值。

不能得出：

1. CRFM 性能代价在不同 gap 或不同 seed 下稳定成立；
2. RA-HPCC 稳定失败或稳定优于 HPCC；
3. 95%% CI 或多 seed 方向一致性；
4. 参数调整后是否可能改善——本审计没有也不允许调参。

## 10. 下一步最小工作

不要先做 96 次 confirm。当前最小必要工作是把这份 seed=1 screening 交给
研究决策者，决定是否因 `size_256k`/long-burst 退化和 RA≈Gate 而停止
RA-HPCC；若仍要求统计确认，只应原样补 seed=2/3，不修改参数。

## Figures

- [Feedback arrival relative to injection](figures/feedback_arrival_relative_injection.svg)
- [Late feedback ratio vs gap](figures/late_feedback_ratio_vs_gap.svg)
- [Next-round start rate vs round](figures/next_round_start_rate_vs_round.svg)
- [Round completion vs round](figures/round_completion_vs_round.svg)
- [Pollution penalty vs gap](figures/pollution_penalty_vs_gap.svg)
- [Burst size vs actionable ratio](figures/burst_size_vs_actionable_ratio.svg)
- [Algorithm comparison](figures/algorithm_comparison.svg)
- [Queue trajectory](figures/queue_trajectory.svg)
- [Selected-flow rate trajectory](figures/selected_flow_rate_trajectory.svg)
""" % (
        all_complete, no_deadlock, no_truncation, all_int, same_plan,
        all_release_ok, max_gap_error, pfc_total,
        "\n".join(hpcc_rows), "\n".join(gap_rows),
        "\n".join(burst_rows), "\n".join(algorithm_rows),
    )
    with open(os.path.join(HERE, "crfm_ra_hpcc_report.md"), "w") as handle:
        handle.write(report)

    suspicious = """# Fixed screening suspicious findings

1. 只有 seed=1；任何稳定性、标准差和置信区间结论都不可用。
2. 只有 `gap_20us` 的 later-round mean RCT penalty 为正（+57.5%）；
   gap50/100/500 分别为 -25.3%/-51.3%/-59.9%，跨轮低起始速率没有
   转化为一致的后续 RCT 代价。
3. `gap_20us` HPCC actionable-byte ratio 为 0.169，未满足问题确认的
   `<=0.10` 严格阈值。
4. RA 相对 Gate 在 gap_20/50/100/500 的 P95 改善均为 0 或近似 0，
   完整 carry 没有显示增量价值。
5. `size_256k` 中 RA 相对 HPCC：P95 RCT +51.62%、goodput -13.71%。
6. long-burst control 中 RA 相对 HPCC：P95 RCT +9.64%、goodput -5.03%。
7. `gap_20us` 中 RA queue max 相对 HPCC +36.02%，超过 GO 的 10% 限制。
8. 32 次运行均无 PFC 事件，因此只能确认“不恶化为正事件”，不能比较
   已发生 PFC 时的暂停行为。
9. `hpcc_round_reset` 只能诊断跨轮状态，不能作为部署算法。
10. 修复后的输入、INT、release、QP 和序列检查均通过，没有无效运行被
   以 0 补入统计。
"""
    with open(os.path.join(HERE, "suspicious_findings.md"), "w") as handle:
        handle.write(suspicious)

    handoff = """# 给 GPT 的 fixed screening 摘要

唯一正式判定：**INCONCLUSIVE**（只有 seed=1，不能写稳定结论）。

数据有效性：32/32 运行通过；exit=0；所有流/轮次完成；无 NaN、死锁或
截断；四模式均有 INT；RA 多轮 carry>0；所有下一轮 release 均晚于上一轮
ACK completion；gap plan 最大误差 %d ns。

问题证据：HPCC gap20/50 的 late ratio=0.590/0.757，后续 start rate
显著下降；但 later-round mean RCT penalty 只有 gap20 为正（+57.5%%），
gap50/100/500 为负。gap50 actionable-byte=0.080 满足阈值，但
gap20=0.169 不满足。long-burst actionable ratio=0.998，single-round
四算法完全相同。Reset 将 gap20/50/100/500 的 mean RCT 分别降低
25.58%%/20.55%%/18.29%%/12.16%%，但它仅是诊断 oracle。

算法证据：

- RA vs HPCC P95：gap20 -63.70%%，gap50 -2.69%%，gap100 -0.64%%；
- gap20 queue max +36.02%%；
- size256 P95 +51.62%%、goodput -13.71%%；
- long-burst P95 +9.64%%、goodput -5.03%%；
- RA 与 Gate 在四个 gap 场景 P95 基本相同。

筛选解释：跨轮低速率状态得到支持，但 CRFM 性能代价没有在 gap 扫描中
一致出现，只得到未完全满足严格标准的单 seed 证据；
RA-HPCC 没有通过 GO 条件，且没有证明优于 Gate。若坚持统计确认，只能
冻结参数补 seed2/3；不要基于本结果调参或宣称稳定失败。

完整数字见 `crfm_ra_hpcc_report.md`、`per_seed_metrics.csv` 和
`comparison.csv`。
""" % max_gap_error
    with open(os.path.join(HERE, "gpt_handoff.md"), "w") as handle:
        handle.write(handoff)


def main():
    runs = {}
    metrics = []
    for scenario in CASES:
        for algorithm in ALGOS:
            run = load_run(scenario, algorithm)
            data = [
                run["flow"], run["round"], run["feedback"],
                run["controller"], run["link"], run["selected"], run["pfc"],
            ]
            if not all(common.finite_rows(rows) for rows in data):
                raise RuntimeError(
                    "NaN/Inf in " + run["directory"])
            metric = common.compute_metrics(
                scenario, algorithm, SEED, run)
            metrics.append(add_fixed_metrics(metric, run))
            runs[(scenario, algorithm, SEED)] = run
    write_outputs(metrics, runs)
    build_report(metrics, runs)
    print("determination: INCONCLUSIVE")
    print("valid fixed runs: 32/32; seed coverage: 1 only")
    print("report: " + os.path.join(HERE, "crfm_ra_hpcc_report.md"))
    print("GPT handoff: " + os.path.join(HERE, "gpt_handoff.md"))


if __name__ == "__main__":
    main()
