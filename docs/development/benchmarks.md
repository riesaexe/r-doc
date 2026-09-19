---
id: DEV-BENCHMARKS-001
type: guide
status: active
title: Agent benchmark 与性能基线
created: 2026-09-15
updated: 2026-09-19
---

# Agent benchmark 与性能基线

## 目标

本项目已经具备 versioned cases、机器规则、完整证据 schema 和校验器；本阶段只把它推进到可实证测量，不把示例证据冒充真实 Agent 结果。

## 两层 benchmark 与性能基线

1. **Conformance Benchmark / skill-layer ablation**：使用固定 fixture 和固定 prompt 捕获真实 Codex/其他代理的结构化 trace 和 evidence，分别运行 r-doc 条件与 `baseline-no-r-doc` 条件。固定 prompt 已给出 activation、读取策略和命令顺序，因此 activation 指标是 protocol compliance；当前三个 review 维度也由 Agent 自评，`task_success` 不是独立 grader 的客观成功率。
2. **Naturalistic Effectiveness Benchmark**：只给真实用户任务，不给 activation 答案、required/allowed reads、命令序列或“必须使用 r-doc”的提示；由独立 capture runner 在 Agent 退出后生成最终仓库快照，从原始 CLI JSONL 和 workspace diff 规范化 action trace，并由 grader 在临时物化目录中执行 pytest、行为检查和 documentation assertion。协议和任务 portfolio 见 [benchmarks/naturalistic/README.md](../../benchmarks/naturalistic/README.md)。
3. **确定性审计性能基线**：在 100、1000、5000 个 Markdown 文档夹具上测量审计耗时，记录中位数、p95、Python 和平台信息。

三者不能混为一谈：性能基线不是 Agent benchmark，Conformance 结果不是 natural activation 结果，`example-evidence.json`、task fixture 或 regression test 也不是实战结果。

## 当前状态

只有存在真实、结构化且与 evidence 交叉一致的 `trace.jsonl`、`evidence.json` 且通过评测器后，才能生成可比较的 conformance `result.json`。当前本机已捕获 3 组 Codex `gpt-5.5` skill-layer paired runs，`summary.json` 为 `partial`：trend readiness 已满足，statistical/strong readiness 仍未满足；失败的真实 capture 保存在 `benchmarks/invalid-captures/`，不进入正式汇总。Naturalistic 层现在也有 4 对真实 Codex `gpt-5.5` capture，覆盖 4 个任务，聚合为 `partial`；`coverage_pair_count=4`、`replicated_task_count=0`、`min_pairs_per_task=1`，没有任何任务达到 trend readiness。8 次运行都因 `secrets.md` 而 context safety 失败，另有 baseline CLI run 明确使用 `rg --hidden` 并真实命中 `.env`，故没有正向 effectiveness 结论。统计、多模型和 context-safe 成功运行仍未具备。

已获用户确认并完成扩展的 `gpt-5.6-luna` naturalistic 批次聚合结果发布在 `benchmarks/naturalistic-runs-20260919-luna/summary.json`：4 个任务各 10 个 paired A/B，共 80 次 measurement-valid 运行、40 个配对，全部达到 strong-evidence 样本量门槛；该批次仍是单模型观测，76/80 次因 forbidden reads 失败，两个条件的 task_success/context_safety 均为 5%，因此不能作为正向 effectiveness 结论。原始 CLI trace/log 含机器路径，仅保留在本地审计目录，公开提交只包含聚合 summary。

## 采集前的模型确认门禁

真实 Agent benchmark 和测试数据采集必须把模型选择当作实验参数处理。启动新一轮 run 前，维护者或 Agent 必须先向用户说明准确的模型名称、`with-r-doc`/`baseline-no-r-doc` 配对方案、重复次数和预计采集范围，并获得用户明确确认；默认模型、当前可用模型或工具列表中的模型都不构成授权。确认后的模型名称必须原样写入每个 `run.json` 和汇总结果；更换模型必须创建可区分的新实验批次，不能与既有模型静默混合。该门禁同样适用于只补跑一个模型或调整重复次数的采集。

## Trace 与 evidence 的一致性门禁

聚合器不会把 trace 当作“存在即通过”的附件。JSONL 必须包含带 manifest 元数据绑定的 `trace_start`、连续序号、每个 scenario 的 `scenario_start`/`scenario_end`、规范化 action 事件和 `trace_end`。schema 2 的闭合事件集合还必须从 trace 独立记录 `prompt`、`activation_decision`、`skill_selected`、`governance_report`、`final_response`、`diff_snapshot` 和每个 review 维度；它再派生并逐场景交叉验证所有 evidence 字段、路径、读取、写入、有序命令和退出码。非法 JSON、未知事件或字段、场景覆盖缺失、manifest 不一致、敏感值或任何差异都会使汇总失败。派生的场景证据会保留在 `summary.json` 的 `runs[*].trace_derived`，便于复核。

这证明的是可解析结构和 trace/evidence 一致性，不是对外部采集系统来源的密码学证明。真实运行仍必须保存原始捕获 trace，而不能用一行占位事件替代。

## 配对汇总与读取策略

`profiles` 现在始终按 condition 分层，避免把 `with-r-doc` 与 `baseline-no-r-doc` 平均到同一 profile。`paired_comparisons` 按 `agent + model + task_id + run_id` 匹配同一重复实验，输出两条件的指标均值、with-r-doc 减 baseline 的 delta、每个指标的 mean/median/stdev 和 95% Student-t 区间；每个 comparison 仍分别报告 3/5/10 对 readiness。Naturalistic 顶层 coverage 使用 `coverage_pair_count` 表示跨任务覆盖量，并同时报告按 agent/model comparison group 的最小任务配对数 `task_pair_counts`、`replicated_task_count`、`min_pairs_per_task`、`tasks_with_trend_readiness`、`tasks_with_statistical_readiness` 和 `tasks_with_strong_evidence_readiness`，不会把不同任务各一对误读成一次任务的重复实验，也不会把第二个模型的一次配对误当作同一模型的重复运行。这些 delta 只适用于 skill-layer ablation；manifest 或 trace 校验失败的运行仍保留在 `runs` 供审计，但不会进入 profile 或 paired 汇总。

每个 scenario 同时声明 `required_files_read`、`allowed_files_read` 和 `forbidden_files_read`。required 必须是 allowed 的子集，unnecessary reads 计算为实际读取集合减 allowed 集合，forbidden reads 单独报告。这样 `docs/api.md`、`docs/testing.md` 这类场景依赖不会因为不是“最低必读集合”而产生噪声。命中 `forbidden_files_read` 会把通过的 `context_economy` 降为 `partial`；严格评测和聚合器会直接拒绝该运行。

真实 Codex 捕获使用固定模板和本机 CLI 凭据：

```bash
python benchmarks/capture_codex.py --profile codex-gpt-5.5 --run-id run-001 --condition with-r-doc --model gpt-5.5
python benchmarks/capture_codex.py --profile baseline-no-r-doc --run-id run-001 --condition baseline-no-r-doc --model gpt-5.5
```

捕获器只保存 Agent 实际写出的 `benchmark-evidence.json` 和 `benchmark-trace.jsonl`，同时保存脱敏的 CLI 事件流；缺少任一产物就失败，不从 case 定义合成证据。

Naturalistic 捕获使用独立入口，每次只给 Agent task 的 `user_prompt`：

```bash
python benchmarks/naturalistic/capture_codex.py --task benchmarks/naturalistic/tasks/api-response-field-rename.json --profile codex-gpt-5.5 --run-id run-001 --condition with-r-doc --model gpt-5.5
python benchmarks/naturalistic/capture_codex.py --task benchmarks/naturalistic/tasks/api-response-field-rename.json --profile baseline-no-r-doc --run-id run-001 --condition baseline-no-r-doc --model gpt-5.5
python benchmarks/naturalistic/aggregate.py --root benchmarks/naturalistic-runs
```

该 runner 在 Agent 进程结束后独立读取临时 workspace 生成 `final-state.json`，由原始 Codex JSONL 和 workspace diff 生成规范化 trace，记录采用 LF 规范哈希的 `artifact-hashes.json`，并调用 grader。grader 会重新物化快照并执行声明式 pytest、callable behavior 和文档断言；文本 artifact 的校验兼容 LF/CRLF checkout 差异，但仍拒绝实质内容篡改、没有 runner provenance 或 hash 不一致的运行。命令级 trace inference 遵守 `rg` 默认排除 hidden、`rg --hidden` 才覆盖 hidden、`rg --files` 只列路径，以及 `Get-ChildItem`/`git status` 不读取内容；它仍不等同于 sandbox/file-access telemetry。自然任务聚合按 `agent + model + task_id + run_id` 配对，并分别报告任务级重复、多任务和多模型覆盖。

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

These are not interchangeable: the performance baseline is not an Agent benchmark, the conformance result is not a natural-activation result, and a naturalistic task specification or regression fixture is not a naturalistic effectiveness result.

### Current status

Only real, structured, evaluator-passing `trace.jsonl` and `evidence.json` artifacts may produce comparable conformance results. The repository has three matched Codex `gpt-5.5` skill-layer pairs. `summary.json` is `partial`: trend readiness is true, while statistical and strong-evidence readiness are false. Invalid captures remain under `benchmarks/invalid-captures/` and are excluded from aggregation. Naturalistic aggregation now has four matched real pairs across four tasks from one model and is also `partial`; `coverage_pair_count` is 4, `replicated_task_count` is 0, `min_pairs_per_task` is 1, and no task reaches trend readiness. All eight runs fail context safety on `secrets.md`; one baseline CLI run also explicitly used `rg --hidden` and therefore has a genuine `.env` hit. This is not a positive effectiveness result.

An approved and extended `gpt-5.6-luna` naturalistic batch is published as `benchmarks/naturalistic-runs-20260919-luna/summary.json`: four tasks, ten paired A/B repetitions per task, 80 measurement-valid runs, and 40 complete pairs. It reaches the strong-evidence sample-size threshold per task, but remains a single-model observation; 76 of 80 runs fail on forbidden reads and both conditions average 5% task success/context safety, so it is not a positive effectiveness claim. Raw CLI traces and logs remain local because they contain machine-specific paths.

### Model-selection approval gate

Real Agent benchmarks and test-data capture must treat model choice as an experimental parameter. Before starting a new run batch, the maintainer or Agent must tell the user the exact model names, the `with-r-doc`/`baseline-no-r-doc` pairing, the repetition count, and the intended capture scope, then receive explicit confirmation. A default model, a currently available model, or a model listed by a tool is not authorization. The confirmed model names must be copied verbatim into every `run.json` and aggregate; changing models requires a distinct experiment batch and must not be silently mixed with existing data. The same gate applies when rerunning only one model or changing the repetition count.

### Trace/evidence gate

The aggregator requires manifest-bound `trace_start`, contiguous sequences, scenario lifecycle events, normalized action events, and `trace_end`. Schema 2 independently records prompt, activation decision, selected skill, governance report, final response, diff snapshot, and review dimensions, then derives and cross-checks evidence paths, reads, writes, ordered commands, and exit codes. Unknown JSON or fields, missing scenarios, metadata mismatches, sensitive values, or any evidence difference fail aggregation. This proves structural consistency, not cryptographic provenance; retain the sanitized raw CLI capture for manual review.

### Pairing and read policy

Profiles remain separated by condition. `paired_comparisons` matches `agent + model + task_id + run_id` and reports condition means, with-r-doc minus baseline deltas, mean/median/stdev, and 95% Student-t intervals. The naturalistic top-level summary distinguishes total coverage pairs from repeated pairs per task; its task counts use the minimum paired count across agent/model comparison groups, so a second model's single pair does not masquerade as repeated runs for the first model. Readiness lists are task-scoped rather than portfolio sums. Each scenario declares required, allowed, and forbidden reads. Forbidden reads lower a passing context-economy review to `partial` in ordinary evaluation and fail strict evaluation and aggregation.

### Reproducible commands

```bash
python skills/r-doc/scripts/aggregate_benchmarks.py --root benchmarks
python skills/r-doc/scripts/benchmark_audit.py \
  --sizes 100,1000,5000 --iterations 10 --warmup 0 \
  --output benchmarks/performance-baseline.json
```

The performance values are local trend data, not CI thresholds or complexity guarantees. The current Windows/Python 3.12 snapshot is 0.570s / 0.648s p95 at 100 documents, 6.962s / 9.416s p95 at 1,000, and 28.586s / 30.832s p95 at 5,000.

Back to: [development index](README.md) · [documentation index](../README.md)
