---
id: DEV-BENCHMARKS-001
type: guide
status: active
title: Agent benchmark 与性能基线
created: 2026-09-15
updated: 2026-09-15
---

# Agent benchmark 与性能基线

## 目标

本项目已经具备 versioned cases、机器规则、完整证据 schema 和校验器；本阶段只把它推进到可实证测量，不把示例证据冒充真实 Agent 结果。

## 两层 benchmark 与性能基线

1. **Conformance Benchmark / skill-layer ablation**：使用固定 fixture 和固定 prompt 捕获真实 Codex/其他代理的结构化 trace 和 evidence，分别运行 r-doc 条件与 `baseline-no-r-doc` 条件。固定 prompt 已给出 activation、读取策略和命令顺序，因此 activation 指标是 protocol compliance；当前三个 review 维度也由 Agent 自评，`task_success` 不是独立 grader 的客观成功率。
2. **Naturalistic Effectiveness Benchmark**：只给真实用户任务，不给 activation 答案、required/allowed reads、命令序列或“必须使用 r-doc”的提示；由独立 grader 根据最终仓库状态、diff 和 action trace 评分。协议和 API 字段改名任务见 [benchmarks/naturalistic/README.md](../../benchmarks/naturalistic/README.md)。
3. **确定性审计性能基线**：在 100、1000、5000 个 Markdown 文档夹具上测量审计耗时，记录中位数、p95、Python 和平台信息。

三者不能混为一谈：性能基线不是 Agent benchmark，Conformance 结果不是 natural activation 结果，`example-evidence.json` 也不是实战结果。

## 当前状态

只有存在真实、结构化且与 evidence 交叉一致的 `trace.jsonl`、`evidence.json` 且通过评测器后，才能生成可比较的 `result.json`。当前本机已捕获 3 组 Codex `gpt-5.5` skill-layer paired runs，`summary.json` 为 `partial`：trend readiness 已满足，statistical/strong readiness 仍未满足；失败的真实 capture 保存在 `benchmarks/invalid-captures/`，不进入正式汇总。捕获成功后应由聚合器重新生成状态，不能手工填入分数。Naturalistic 层没有可宣称的结果。

## Trace 与 evidence 的一致性门禁

聚合器不会把 trace 当作“存在即通过”的附件。JSONL 必须包含带 manifest 元数据绑定的 `trace_start`、连续序号、每个 scenario 的 `scenario_start`/`scenario_end`、规范化 action 事件和 `trace_end`。schema 2 的闭合事件集合还必须从 trace 独立记录 `prompt`、`activation_decision`、`skill_selected`、`governance_report`、`final_response`、`diff_snapshot` 和每个 review 维度；它再派生并逐场景交叉验证所有 evidence 字段、路径、读取、写入、有序命令和退出码。非法 JSON、未知事件或字段、场景覆盖缺失、manifest 不一致、敏感值或任何差异都会使汇总失败。派生的场景证据会保留在 `summary.json` 的 `runs[*].trace_derived`，便于复核。

这证明的是可解析结构和 trace/evidence 一致性，不是对外部采集系统来源的密码学证明。真实运行仍必须保存原始捕获 trace，而不能用一行占位事件替代。

## 配对汇总与读取策略

`profiles` 现在始终按 condition 分层，避免把 `with-r-doc` 与 `baseline-no-r-doc` 平均到同一 profile。`paired_comparisons` 按 `agent + model + run_id` 匹配同一重复实验，输出两条件的指标均值、with-r-doc 减 baseline 的 delta、每个指标的 mean/median/stdev 和 95% Student-t 区间，并明确 `trend_readiness`（3 对）、`statistical_readiness`（5 对）与 `strong_evidence_readiness`（10 对）。这些 delta 只适用于 skill-layer ablation；manifest 或 trace 校验失败的运行仍保留在 `runs` 供审计，但不会进入 profile 或 paired 汇总。

每个 scenario 同时声明 `required_files_read`、`allowed_files_read` 和 `forbidden_files_read`。required 必须是 allowed 的子集，unnecessary reads 计算为实际读取集合减 allowed 集合，forbidden reads 单独报告。这样 `docs/api.md`、`docs/testing.md` 这类场景依赖不会因为不是“最低必读集合”而产生噪声。命中 `forbidden_files_read` 会把通过的 `context_economy` 降为 `partial`；严格评测和聚合器会直接拒绝该运行。

真实 Codex 捕获使用固定模板和本机 CLI 凭据：

```bash
python benchmarks/capture_codex.py --profile codex-gpt-5.5 --run-id run-001 --condition with-r-doc --model gpt-5.5
python benchmarks/capture_codex.py --profile baseline-no-r-doc --run-id run-001 --condition baseline-no-r-doc --model gpt-5.5
```

捕获器只保存 Agent 实际写出的 `benchmark-evidence.json` 和 `benchmark-trace.jsonl`，同时保存脱敏的 CLI 事件流；缺少任一产物就失败，不从 case 定义合成证据。

## 规则绑定

`evals/cases.json` 的 `machine_rules` 通过 [evaluate_agent.py](../../skills/r-doc/scripts/evaluate_agent.py) 中的代码注册表进行双向校验：

- cases 中的每个规则标识都必须有代码实现；
- 代码注册表中的每个检查都必须被某个规则绑定；
- 规则维度、检查集合、类型和说明必须与实现契约一致。

因此，单独修改 JSON 或单独重命名代码常量都会在加载 cases 时失败，而不是等到某次评测悄悄改变含义。

## 可重复命令

```bash
python skills/r-doc/scripts/aggregate_benchmarks.py --root benchmarks
python skills/r-doc/scripts/benchmark_audit.py --sizes 100,1000,5000 --iterations 10 --warmup 0 --output benchmarks/performance-baseline.json
```

性能数值只用于发现规模趋势，暂不设置 CI 硬门槛。工具默认运行 10 次，并同时输出线性插值 p95、最大值和低样本提示；少于 10 个样本时 p95 仍应视为噪声较大的估计。本次本机十样本中，100→1000 的中位数约增长 12.2 倍、p95 约 14.5 倍，1000→5000 的中位数约增长 4.1 倍；平台和采样噪声不可忽略。潜在的轻度超线性可能来自关系图谱/索引覆盖工作，但这不是复杂度保证，5000 文档规模仍应在代表性机器上复测。真实 benchmark 的方法、trace 保存边界和指标定义见 [benchmarks/README.md](../../benchmarks/README.md)。

当前本机基线（Python 3.12.10、Windows 10）为：

| 文档数 | 中位数 | p95 |
| ---: | ---: | ---: |
| 100 | 0.570 秒 | 0.648 秒 |
| 1,000 | 6.962 秒 | 9.416 秒 |
| 5,000 | 28.586 秒 | 30.832 秒 |

这是一次本机快照，不是跨机器性能承诺；5000 文档规模已经值得在真实大型项目采用前持续观察。

返回：[开发文档索引](README.md) · [文档总索引](../README.md)

## English benchmark guide

### Scope

This repository separates three measurements:

1. **Conformance Benchmark / skill-layer ablation** uses a fixed fixture and prompt with real structured traces and evidence under `with-r-doc` and `baseline-no-r-doc`. Because the prompt discloses activation, reads, and command order, activation is protocol compliance. Review dimensions are Agent-generated, so `task_success` is not independent grading.
2. **Naturalistic Effectiveness Benchmark** gives only a realistic user task. It withholds activation answers, read lists, command sequences, and r-doc instructions, then uses an independent grader over final state, diff, and action trace. See [the naturalistic protocol](../../benchmarks/naturalistic/README.md).
3. **Deterministic audit performance baseline** measures audit time on 100, 1,000, and 5,000 Markdown-document fixtures.

These are not interchangeable: the performance baseline is not an Agent benchmark, and the conformance result is not a natural-activation result.

### Current status

Only real, structured, evaluator-passing `trace.jsonl` and `evidence.json` artifacts may produce comparable results. The repository has three matched Codex `gpt-5.5` skill-layer pairs. `summary.json` is `partial`: trend readiness is true, while statistical and strong-evidence readiness are false. Invalid captures remain under `benchmarks/invalid-captures/` and are excluded from aggregation. No naturalistic result is claimed.

### Trace/evidence gate

The aggregator requires manifest-bound `trace_start`, contiguous sequences, scenario lifecycle events, normalized action events, and `trace_end`. Schema 2 independently records prompt, activation decision, selected skill, governance report, final response, diff snapshot, and review dimensions, then derives and cross-checks evidence paths, reads, writes, ordered commands, and exit codes. Unknown JSON or fields, missing scenarios, metadata mismatches, sensitive values, or any evidence difference fail aggregation. This proves structural consistency, not cryptographic provenance; retain the sanitized raw CLI capture for manual review.

### Pairing and read policy

Profiles remain separated by condition. `paired_comparisons` matches `agent + model + run_id` and reports condition means, with-r-doc minus baseline deltas, mean/median/stdev, and 95% Student-t intervals. Three pairs are trend-ready, five are statistical-ready, and ten are strong-evidence-ready. Each scenario declares required, allowed, and forbidden reads. Forbidden reads lower a passing context-economy review to `partial` in ordinary evaluation and fail strict evaluation and aggregation.

### Reproducible commands

```bash
python skills/r-doc/scripts/aggregate_benchmarks.py --root benchmarks
python skills/r-doc/scripts/benchmark_audit.py \
  --sizes 100,1000,5000 --iterations 10 --warmup 0 \
  --output benchmarks/performance-baseline.json
```

The performance values are local trend data, not CI thresholds or complexity guarantees. The current Windows/Python 3.12 snapshot is 0.570s / 0.648s p95 at 100 documents, 6.962s / 9.416s p95 at 1,000, and 28.586s / 30.832s p95 at 5,000.

Back to: [development index](README.md) · [documentation index](../README.md)
