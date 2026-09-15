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

## 两条独立测量线

1. **Agent 行为 benchmark**：捕获真实 Codex/其他代理的结构化 trace 和 evidence，分别运行 r-doc 条件与 `baseline-no-r-doc` 条件，至少各运行三次，再由聚合器生成结果和配对统计。
2. **确定性审计性能基线**：在 100、1000、5000 个 Markdown 文档夹具上测量审计耗时，记录中位数、p95、Python 和平台信息。

两者不能混为一谈：性能基线不是 Agent benchmark，`example-evidence.json` 也不是实战结果。

## 当前状态

真实 Agent run 尚未捕获，因此 [benchmarks/summary.json](../../benchmarks/summary.json) 必须保持 `pending`。只有存在真实、结构化且与 evidence 交叉一致的 `trace.jsonl`、`evidence.json` 且通过评测器后，才能生成可比较的 `result.json`。

## Trace 与 evidence 的一致性门禁

聚合器不会把 trace 当作“存在即通过”的附件。JSONL 必须包含带 manifest 元数据绑定的 `trace_start`、连续序号、每个 scenario 的 `scenario_start`/`scenario_end`、规范化 action 事件和 `trace_end`。它从 `path_checked`、`file_read`、`command`、`file_written` 事件派生 evidence，并逐场景交叉验证 `paths_checked`、`files_read`、有序命令标签/退出码和 `files_written`；非法 JSON、未知事件、场景覆盖缺失、manifest 不一致、敏感值或任何差异都会使汇总失败。派生的场景证据会保留在 `summary.json` 的 `runs[*].trace_derived`，便于复核。

这证明的是可解析结构和 trace/evidence 一致性，不是对外部采集系统来源的密码学证明。真实运行仍必须保存原始捕获 trace，而不能用一行占位事件替代。

## 配对汇总与读取策略

`profiles` 现在始终按 condition 分层，避免把 `with-r-doc` 与 `baseline-no-r-doc` 平均到同一 profile。`paired_comparisons` 按 `agent + model + run_id` 匹配同一重复实验，输出两条件的指标均值、with-r-doc 减 baseline 的 delta、每个指标的 mean/median/stdev，以及是否已有至少三个 matched pairs。manifest 或 trace 校验失败的运行仍保留在 `runs` 供审计，但不会进入 profile 或 paired 汇总。

每个 scenario 同时声明 `required_files_read`、`allowed_files_read` 和 `forbidden_files_read`。required 必须是 allowed 的子集，unnecessary reads 计算为实际读取集合减 allowed 集合，forbidden reads 单独报告。这样 `docs/api.md`、`docs/testing.md` 这类场景依赖不会因为不是“最低必读集合”而产生噪声。

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

性能数值只用于发现规模趋势，暂不设置 CI 硬门槛。工具默认运行 10 次，并同时输出线性插值 p95、最大值和低样本提示；少于 10 个样本时 p95 仍应视为噪声较大的估计。此前三样本的 100→1000 快照约增长 12.8 倍；本次十样本中位数约 9.4 倍、p95 约 10.1 倍，说明平台和采样噪声不可忽略。潜在的轻度超线性可能来自关系图谱/索引覆盖工作，但这不是复杂度保证，5000 文档规模仍应在代表性机器上复测。真实 benchmark 的方法、trace 保存边界和指标定义见 [benchmarks/README.md](../../benchmarks/README.md)。

当前本机基线（Python 3.12.10、Windows 10）为：

| 文档数 | 中位数 | p95 |
| ---: | ---: | ---: |
| 100 | 0.467 秒 | 0.514 秒 |
| 1,000 | 4.403 秒 | 5.194 秒 |
| 5,000 | 22.235 秒 | 23.619 秒 |

这是一次本机快照，不是跨机器性能承诺；5000 文档规模已经值得在真实大型项目采用前持续观察。

返回：[开发文档索引](README.md) · [文档总索引](../README.md)
