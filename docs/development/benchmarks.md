---
id: DEV-BENCHMARKS-001
type: guide
status: active
title: Agent benchmark 与性能基线
created: 2026-09-15
updated: 2026-09-23
---

# Agent benchmark 与性能基线

## 目标

本项目已经具备 versioned cases、机器规则、完整证据 schema 和校验器；本阶段只把它推进到可实证测量，不把示例证据冒充真实 Agent 结果。

## 两层 benchmark 与性能基线

1. **Conformance Benchmark / skill-layer ablation**：使用固定 fixture 和固定 prompt 捕获真实 Codex/其他代理的结构化 trace 和 evidence，分别运行 r-doc 条件与 `baseline-no-r-doc` 条件。固定 prompt 已给出 activation、读取策略和命令顺序，因此 activation 指标是 protocol compliance；当前三个 review 维度也由 Agent 自评，`task_success` 不是独立 grader 的客观成功率。
2. **Naturalistic Effectiveness Benchmark**：只给真实用户任务，不给 activation 答案、required/allowed reads、命令序列或“必须使用 r-doc”的提示；由独立 capture runner 在 Agent 退出后生成最终仓库快照，从原始 CLI JSONL 和 workspace diff 规范化 action trace，并由 grader 在临时物化目录中执行 pytest、行为检查和 documentation assertion。当前 runner 还给两种条件施加相同的敏感路径保护和有界搜索底线，因此新增批次不把这部分安全收益单独归因给 r-doc。协议和任务 portfolio 见 [benchmarks/naturalistic/README.md](../../benchmarks/naturalistic/README.md)。
3. **确定性审计性能基线**：在 100、1000、5000 个 Markdown 文档夹具上测量审计耗时，记录中位数、p95、Python 和平台信息。

三者不能混为一谈：性能基线不是 Agent benchmark，Conformance 结果不是 natural activation 结果，`example-evidence.json`、task fixture 或 regression test 也不是实战结果。

## 当前状态

只有存在真实、结构化且与 evidence 交叉一致的 `trace.jsonl`、`evidence.json` 且通过评测器后，才能生成可比较的 conformance `result.json`。历史 3 组 Codex `gpt-5.5` skill-layer paired runs 仍以 0.2.15 合约保留在 `benchmarks/summary-v0.2.15.json`；当前 `benchmarks/summary.json` 已按 0.4.0 合约重放并明确为 `fail`，六个 run 因版本门不匹配保留在审计结果中。Naturalistic 层的历史 capture 也已按当前 grader 重放：`benchmarks/naturalistic-runs/summary.json` 保留 44 条记录，但当前 measurement-valid 与 verified activation 均为 0。修复后的 Luna 批次已完成 80 次运行，当前 `summary.json` 有 49 次 measurement-valid（40 次 baseline activation 不适用，9 次 `with-r-doc` 完成 visible/load/use），形成 9 个完整配对覆盖 3 个任务；CLI 没有 verified `with-r-doc` 配对。该批次仍是 `fail`，6 次整体通过、74 次门禁失败，其中 67 次包含 forbidden-read 证据，31 次未观察到 Skill use；3 次目录枚举误报已移除，因此只能用于诊断和小样本探索。

已获用户确认并按新 runner 完成、再经归因修复重放的 `gpt-5.6-luna` naturalistic 批次位于 `benchmarks/naturalistic-runs-20260919-luna-v0.3.0-rerun/`，包含 4 个任务各 10 个 paired A/B，共 80 次运行。49 次通过当前 measurement/hash 门（40 次 baseline activation 不适用，9 次 `with-r-doc` 完成 visible/load/use），形成 9 个完整配对，覆盖 API、event、SQL 三个任务；CLI 的 `with-r-doc` 运行没有形成 verified 配对。聚合结果为 `fail`，6 次整体通过、74 次门禁失败；67 次包含 forbidden-read 证据，31 次缺少 use 证据，其中 6 次任务结果本身通过但激活未验证。3 次目录枚举误报已被修复。这个批次已能用于检查新 runner 和 fixture 问题，但 3 对/任务、单模型且存在大规模安全失败，不能作为 Skill 增量效果结论。原始 CLI trace/log 含机器路径，脱敏后的逐次证据在 `public-evidence.json`。

后续 naturalistic capture 的 runner preflight 已升级为 `skill-discovery-safe-read-preflight-v2-command-glob`：两种条件共享敏感路径保护和有界搜索底线，并能正确识别嵌套 PowerShell 引号中的保护路径排除 glob，禁止从项目根执行 `rg --hidden` 等无限制内容扫描。该变化会削弱“r-doc 单独防止敏感读取”的可归因性，但能验证系统级安全底线；旧 v1 批次不重写，新协议必须使用新的模型批准批次。

首个新协议小批次 `benchmarks/naturalistic-runs-20260920-luna-v0.3.0-smoke-rdoc-v6-safe-read/` 已完成：`gpt-5.6-luna`、4 个任务各 1 对、共 8 次运行。forbidden read 为 0/8，activation 未验证为 0/8；baseline 4/4 通过，with-r-doc 3/4 通过，唯一失败是 event 任务的运行时契约（缺少 `display_name` 属性）。该批次只验证安全底线，不具备趋势就绪或 Skill 效果结论资格。

该 Event 失败已定位为任务说明歧义导致的过度改名：Agent 把输入对象的 `user.name` 也改成了 `user.display_name`，而独立运行时契约仍按 `user.name` 传参。已新增版本化回归 fixture `benchmarks/naturalistic/tasks/event-payload-rename-v2.json`，明确只改输出 payload key；旧 v6 证据不重写，v2 的新 A/B 结果须在单独、明确批准的采集批次中记录。

Event v2 独立小批次现已完成：`gpt-5.6-luna` 下 baseline 与 with-r-doc 各 1 次，2/2 运行时契约通过，forbidden read 为 0/2，activation 未验证为 0/2。结果目录为 `benchmarks/naturalistic-runs-20260920-luna-v0.3.0-event-v2-contract/`；它验证了 fixture 修复，但单对样本仍低于 Skill 效果的趋势/统计门槛。

随后按新 runner 完成完整批次：`gpt-5.6-luna`、API/CLI/SQL/Event v2 四类任务各 10 对，共 80 次运行。79 次通过，唯一失败是 `sql-column-rename / baseline-no-r-doc / run-002` 读取 `.env` 触发 forbidden-read；activation 未验证为 0/80，四类任务均达到 10 对强证据数量门槛，Event runtime contract 20/20 通过。批次目录为 `benchmarks/naturalistic-runs-20260920-luna-v0.3.0-full-v7-event-v2/`，逐次脱敏证据为其中的 `public-evidence.json`。由于两种条件共用 safe-read preflight 且只覆盖一个模型，该结果用于 runner/fixture 验证，不直接归因 Skill 增量效果。

随后按 v2 command-glob runner 完成后续完整批次：`gpt-5.6-luna`、API/CLI/SQL/Event v2 四类任务各 10 对，共 80 次运行。原始汇总为 79 次通过，forbidden read 为 0/80、activation 未验证为 0/80，SQL 运行全部通过；唯一失败是 `event-payload-rename-v2 / with-r-doc / run-002` 的最终状态检查，`tests/test_events.py` 仍含旧 `user_name`。批次目录为 `benchmarks/naturalistic-runs-20260920-luna-v0.3.0-full-v8-command-glob-event-v2/`，逐次脱敏证据为其中的 `public-evidence.json`。该失败随后被确认为任务契约假阴性；修正后的派生汇总 `summary-regraded-event-contract.json` 报告 80/80 次运行通过。原始结果仍不重写，单模型、共用 preflight 的结果也仍不应直接解释为 Skill 增量效果。

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

该 runner 在 Agent 进程结束后独立读取临时 workspace 生成 `final-state.json`，由原始 Codex JSONL 和 workspace diff 生成规范化 trace，记录 schema 2 的 `artifact-hashes.json`，并调用 grader。文本 artifact 先按 UTF-8 LF 规范化，再做唯一 SHA-256 比对，因此 Git 的 LF/CRLF checkout 差异不会造成误报，但实质内容变化会失败；仓库的 `.gitattributes` 进一步要求 benchmarks 下的可哈希文本在 checkout 时保持 LF，避免外部按原始字节重放时产生平台差异。旧 schema 1 记录不进入当前测量。runner 在可用本机凭据下为每次捕获建立隔离 `CODEX_HOME`，并把 `activation_evidence` 的 visible/load/use 信号写入 manifest。效果比较要求 with-r-doc 三个信号均已观察；Codex JSONL 不提供 OS 级文件访问 telemetry，因而这是捕获面证据而非内核级审计。当前 preflight 还在两种条件中共同要求保护 `.env`、secrets、凭据、密钥和证书路径，并禁止从项目根执行 `rg --hidden` 等无限制内容搜索；这是一条系统级安全底线，不再单独归因给 r-doc。命令级 trace inference 遵守 `rg` 默认排除 hidden、`rg --hidden` 才覆盖 hidden、`rg --files` 只列路径，以及 `Get-ChildItem`/`git status` 不读取内容；它仍不等同于 sandbox/file-access telemetry。自然任务聚合按 `agent + model + task_id + run_id` 配对，并分别报告任务级重复、多任务和多模型覆盖。使用 `benchmarks/naturalistic/export_public_evidence.py` 可导出脱敏的逐次 manifest；原始 trace/log 不必公开。

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
2. **Naturalistic Effectiveness Benchmark** gives only a realistic user task. It withholds activation answers, read lists, command sequences, and r-doc instructions, then uses an independent grader over final state, diff, and action trace. The current runner also applies the same protected-read and bounded-search safety floor to both conditions, so new batches do not attribute that floor solely to r-doc. See [the naturalistic protocol](../../benchmarks/naturalistic/README.md).
3. **Deterministic audit performance baseline** measures audit time on 100, 1,000, and 5,000 Markdown-document fixtures.

These are not interchangeable: the performance baseline is not an Agent benchmark, the conformance result is not a natural-activation result, and a naturalistic task specification or regression fixture is not a naturalistic effectiveness result.

### Current status

Only real, structured, evaluator-passing `trace.jsonl` and `evidence.json` artifacts may produce comparable conformance results. The historical three matched Codex `gpt-5.5` skill-layer pairs remain available under `benchmarks/summary-v0.2.15.json`; the current `benchmarks/summary.json` is regenerated against 0.4.0 and explicitly fails its version gate for all six historical runs. Naturalistic aggregation retains 44 historical records with zero current measurement-valid or activation-verified runs in the formal baseline root. The repaired isolated Luna rerun retains 80 runs and 49 measurement-valid runs: 40 baseline runs are activation-not-applicable and 9 `with-r-doc` runs have complete visible/load/use evidence, producing 9 complete pairs across 3 tasks. Its aggregate has 6 overall passes and 74 gated failures; 67 runs include forbidden-read evidence, 31 `with-r-doc` runs lack observed Skill use, and three path-enumeration false positives were removed. It remains exploratory evidence rather than a Skill-effect conclusion.

The repaired `gpt-5.6-luna` naturalistic batch contains four tasks, ten paired A/B repetitions per task, and 80 runs. Under the previous runner preflight, 49 runs are measurement-valid: 40 baseline runs are activation-not-applicable and 9 `with-r-doc` runs have complete visible/load/use evidence; 9 complete pairs cover 3 tasks, while the CLI task has no verified `with-r-doc` pair. Its aggregate is `fail`: 6 runs pass overall and 74 fail a gate; 67 runs include forbidden-read evidence, 31 `with-r-doc` runs lack observed Skill use, and six failures have a passing task outcome but unverified activation. The three-pair task deltas are exploratory and do not establish incremental Skill effectiveness. A sanitized per-run manifest is available at `benchmarks/naturalistic-runs-20260919-luna-v0.3.0-rerun/public-evidence.json`; raw CLI traces and logs remain local. The common safe-read preflight fix is not retroactively applied to this historical batch.

The first new-protocol smoke batch is `benchmarks/naturalistic-runs-20260920-luna-v0.3.0-smoke-rdoc-v6-safe-read/`: eight `gpt-5.6-luna` runs across four matched task pairs, with zero forbidden-read runs and zero unverified activations. Baseline passes 4/4; `with-r-doc` passes 3/4 because the event task's runtime contract still fails on a missing `display_name` attribute. It is safety-floor validation only and remains below trend-readiness.

The Event failure was caused by task wording that allowed an over-rename: the agent changed the input object from `user.name` to `user.display_name`, while the independent runtime contract continued to pass `user.name`. A versioned regression fixture, `benchmarks/naturalistic/tasks/event-payload-rename-v2.json`, now states that only the emitted payload key changes. The historical v6 evidence is not rewritten; v2 results require a separate explicitly approved capture batch.

The Event v2 isolated smoke batch is now complete: one baseline and one `with-r-doc` run under `gpt-5.6-luna`, both passing the runtime contract, with zero forbidden-read runs and zero unverified activations. Its artifacts are under `benchmarks/naturalistic-runs-20260920-luna-v0.3.0-event-v2-contract/`; this confirms the fixture repair but is below the replication and effectiveness-readiness thresholds.

The complete new-runner batch followed: `gpt-5.6-luna`, ten matched pairs for each of API, CLI, SQL, and Event v2, 80 runs total. Seventy-nine runs pass; the only failure is `sql-column-rename / baseline-no-r-doc / run-002`, where the baseline read `.env` and triggered the forbidden-read gate. Unverified activation is 0/80, every task reaches ten pairs, and the Event runtime contract passes 20/20. The artifacts are under `benchmarks/naturalistic-runs-20260920-luna-v0.3.0-full-v7-event-v2/`; because the safe-read preflight is shared and only one model is covered, this is runner/fixture evidence rather than a direct Skill-increment attribution.

The follow-up full batch used the v2 command-glob runner: `gpt-5.6-luna`, ten matched pairs for each of API, CLI, SQL, and Event v2, 80 runs total. Seventy-nine runs pass; forbidden reads are 0/80, unverified activation is 0/80, all SQL runs pass, and the only failure is `event-payload-rename-v2 / with-r-doc / run-002`, whose final-state check still finds `user_name` in `tests/test_events.py`. The artifacts are under `benchmarks/naturalistic-runs-20260920-luna-v0.3.0-full-v8-command-glob-event-v2/`; this is not a clean all-pass batch, but it removes the v7 SQL baseline forbidden-read attribution problem. Because the safe-read preflight is shared and only one model is covered, it remains runner/fixture evidence rather than a direct Skill-increment attribution.

The Event v2 failure was a task-contract false negative rather than an agent-state failure: the final test correctly contains `display_name` and a runtime assertion that `user_name` is absent, while the old raw `not_contains` assertion incorrectly rejected that test file. The v8 result artifact remains unchanged; regrading the captured snapshot with the corrected contract passes all grader checks. The corrected derived aggregate is `benchmarks/naturalistic-runs-20260920-luna-v0.3.0-full-v8-command-glob-event-v2/summary-regraded-event-contract.json` and reports 80/80 passing runs.

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

The v0.4.1 recapture uses `benchmarks/naturalistic/tasks-v2/` with gpt-5.6-luna, seven task families, ten matched pairs per task, and 140 runs. The 14-run smoke gate passed 14/14 before the full batch started. The full batch has 133 task-outcome passes and 7 failures, zero runner exceptions, 140 verified activation records, and a passing public-evidence cross-check. The failures are preserved as measured outcomes: two command-attribution `.env` false positives, four producer input-contract mistakes in the cross-module task, and one release-baseline confirmation pause. The batch is descriptive-only because the safe-read preflight is shared by both conditions.

这 133/140 是两种条件合并后的任务结果通过数，不是 `with-r-doc` 单独成功率，也不能说明通过结果由 r-doc 造成。7 个失败包含不同性质的问题：2 个读取归因误报、4 个 cross-module 输入契约错误、1 个因等待确认未完成的 release baseline 任务。应保留原始记录，并分别报告测量有效性、任务结果和按条件配对的差值。批次只覆盖 `gpt-5.6-luna`，且两种条件共用 safe-read preflight，因此不能推广到其他模型，也无法估计 r-doc 相对共同安全底线的全部贡献。后续净增益研究需要在新版本批次中修正归因和任务契约、明确写入授权范围，并至少对两个经用户确认的模型分别采集配对样本，报告分模型的条件结果与配对差值。该句是 v0.4.1 报告形成时的状态；2026-09-23 后续已启动并完成用户确认的 v1.0.0 gpt-6-luna 批次，结果见下文。

The 133/140 figure pools task outcomes across both conditions; it is not the `with-r-doc` success rate and does not show that r-doc caused the passing outcomes. The seven failures represent different issues: two read-attribution false positives, four cross-module input-contract errors, and one release-baseline task left incomplete while waiting for confirmation. Preserve the capture and report measurement validity, task outcomes, and paired condition deltas separately. The batch covers only `gpt-5.6-luna`, and both conditions share the safe-read preflight, so it cannot generalize across models or estimate r-doc's full contribution beyond that shared safety floor. A future net-effect study needs a new versioned batch with corrected attribution and task contracts, explicit write authorization, and matched samples for at least two user-approved models, reported by model and condition with paired deltas. That status reflects the v0.4.1 report; a later user-approved v1.0.0 gpt-6-luna batch is recorded below.

## v1.0.0 gpt-6-luna batch

The user-confirmed 2026-09-23 batch completed 140 runs across seven `tasks-v2` task families, ten matched pairs per task, with zero runner exceptions. Task outcomes passed in 124/140 runs; the independent grader overall passed 65 and failed 75. All 70 `with-r-doc` runs have `visibility: unknown`; load/use were observed in 67 and not observed in 3. This leaves zero verified treatment activations and zero valid paired comparisons. The sanitized 140-run evidence and full source-hash replay pass. The result is descriptive-only because both conditions share the safe-read preflight, and it does not establish cross-model generality. Per-task outcomes and failure categories are recorded in the [benchmark index](../../benchmarks/README.md); raw traces and logs remain local.

2026-09-23 经用户确认完成 `gpt-6-luna` v1.0.0 批次：`tasks-v2` 七类任务各 10 对，共 140 次运行，0 个 runner exception。任务 outcome 为 124/140 通过，独立 grader 整体为 65 pass、75 fail。70 个 `with-r-doc` 运行的 visibility 全为 `unknown`，67 次观察到 load/use，3 次没有观察到；因此 verified treatment activation 和有效配对均为 0。脱敏逐次证据及完整源文件哈希重放通过。两种条件共享 safe-read preflight，且本批只覆盖一个模型，因此不能据此建立 r-doc 净效应或跨模型结论。逐任务 outcome 和失败类别见[benchmark 索引](../../benchmarks/README.md)；原始 trace/log 留在本机。

Back to: [development index](README.md) · [documentation index](../README.md)

## Historical evidence-chain status at v0.4.0

The approved v0.4.0 Luna full batch is recorded under benchmarks/naturalistic-runs-20260920-luna-v0.4.0-full-v1-complex/. It uses gpt-5.6-luna with seven task families, ten matched A/B pairs per task, and 140 final run artifacts. The batch has 70 complete pairs, 93 task-outcome passes, 47 task-outcome failures, zero forbidden-read records after command-segment replay, and 70/70 with-r-doc visible/load/use activation records; baseline activation is not applicable. Its aggregate pass is the measurement-gate result; shared safe-read preflight keeps effect attribution descriptive-only. Public-only and local source-hash verification both pass.

A derived regrade is recorded separately under benchmarks/naturalistic-runs-20260920-luna-v0.4.0-full-v1-complex-regraded-v1/. It preserves the original 140 run artifacts and applies the repaired callable argument contract plus explicit natural-language assertion modes. The derived result has 115 task-outcome passes and 25 failures: 8 architecture documentation failures, 12 cross-module contract/index failures, and 5 release-checklist version omissions. This is a deterministic regrade of existing captures, not a new Agent sample, and it does not change the original evidence chain.

The revised complex-task contracts are staged under benchmarks/naturalistic/tasks-v2/. They correct the architecture contract so historical migration context is allowed, make the decision-index update explicit in the cross-module prompt, and define the release checklist as reusable while requiring verification of the current release against the release page. They are future-capture contracts; they do not rewrite the v1 traces.

A contract-only regrade using the original v1 prompts and the relaxed architecture/release assertions is recorded under benchmarks/naturalistic-runs-20260920-luna-v0.4.0-full-v2-contracts-regraded-v1/. It produces 128 task-outcome passes and 12 failures from the same 140 captures; all 12 are cross-module outcomes, consisting of 11 missing decision-index links and one producer field mismatch. This is a regrade, not a new model sample.

The formal naturalistic root is intentionally pending at benchmarks/naturalistic-runs/summary.json. The former 44-record aggregate is preserved as benchmarks/naturalistic-runs/summary-unverified-v0.4.0.json because 36 published result paths are absent: 16 belong to gpt-5.5 and all 20 gpt-5.6-sol records are unsupported by an approved batch. This preserves history without treating incomplete provenance as current evidence.

The public verification tool is benchmarks/naturalistic/verify_public_evidence.py. Without source-root it verifies sanitized structure, exported digests, ordering, and cross-summary identities; with source-root it additionally replays all local artifact hashes. See benchmarks/naturalistic/public-evidence-verification.md for the exact commands and the non-replay limitation of the release tree.

Versioned v2 task specifications under benchmarks/naturalistic/tasks-v2/ cover architecture-decision conflicts, cross-module contract migration, and release-document drift for future captures. The runner records elapsed duration and explicit usage fields when Codex JSON events expose them. Aggregate output also records effect_attribution and marks results descriptive-only when both conditions share the safe-read preflight.
