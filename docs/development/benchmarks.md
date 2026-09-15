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

1. **Agent 行为 benchmark**：捕获真实 Codex/其他代理的 trace 和 evidence，分别运行 r-doc 条件与 `baseline-no-r-doc` 条件，至少各运行三次，再由聚合器生成结果和统计。
2. **确定性审计性能基线**：在 100、1000、5000 个 Markdown 文档夹具上测量审计耗时，记录中位数、p95、Python 和平台信息。

两者不能混为一谈：性能基线不是 Agent benchmark，`example-evidence.json` 也不是实战结果。

## 当前状态

真实 Agent run 尚未捕获，因此 [benchmarks/summary.json](../../benchmarks/summary.json) 必须保持 `pending`。只有存在真实 `trace.jsonl`、`evidence.json` 且通过评测器后，才能生成可比较的 `result.json`。

## 规则绑定

`evals/cases.json` 的 `machine_rules` 通过 [evaluate_agent.py](../../skills/r-doc/scripts/evaluate_agent.py) 中的代码注册表进行双向校验：

- cases 中的每个规则标识都必须有代码实现；
- 代码注册表中的每个检查都必须被某个规则绑定；
- 规则维度、检查集合、类型和说明必须与实现契约一致。

因此，单独修改 JSON 或单独重命名代码常量都会在加载 cases 时失败，而不是等到某次评测悄悄改变含义。

## 可重复命令

```bash
python skills/r-doc/scripts/aggregate_benchmarks.py --root benchmarks
python skills/r-doc/scripts/benchmark_audit.py --sizes 100,1000,5000 --iterations 3 --warmup 0 --output benchmarks/performance-baseline.json
```

性能数值只用于发现规模趋势，暂不设置 CI 硬门槛。真实 benchmark 的方法、trace 保存边界和指标定义见 [benchmarks/README.md](../../benchmarks/README.md)。

当前本机基线（Python 3.12.10、Windows 10）为：

| 文档数 | 中位数 | p95 |
| ---: | ---: | ---: |
| 100 | 0.739 秒 | 0.808 秒 |
| 1,000 | 9.439 秒 | 9.840 秒 |
| 5,000 | 25.025 秒 | 30.174 秒 |

这是一次本机快照，不是跨机器性能承诺；5000 文档规模已经值得在真实大型项目采用前持续观察。

返回：[开发文档索引](README.md) · [文档总索引](../README.md)
