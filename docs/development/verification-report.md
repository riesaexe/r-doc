---
id: VERIFICATION-RDOC-001
type: report
status: active
title: r-doc 可复现验证记录
created: 2026-09-14
updated: 2026-09-19
validation:
  parser: PyYAML BaseLoader
  scenarios:
    - nested-mapping
    - nested-list
---

# r-doc 可复现验证记录

## 摘要

这份记录保存当前源副本的可复现验证结果，避免只在发布说明中口头声称“已验证”。命令均从项目根目录执行，脚本不会修改项目文档。

## 当前结果

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| Skill 包结构、入口、链接和脚本语法 | `python skills/r-doc/scripts/validate_skill.py skills/r-doc` | PASS |
| 安全结构修复预览 | `python skills/r-doc/scripts/repair_docs.py --root .` | PASS，无待写入修复 |
| 项目文档结构、索引、链接、元数据和敏感值 | `python skills/r-doc/scripts/audit_docs.py --root . --strict` | PASS，0 errors / 0 warnings；公开 AWS 文档示例保留为 3 条 informational allowlist 记录 |
| 临时项目行为场景 | `python -m unittest discover -s skills/r-doc/tests -p 'test_*.py'` | PASS，116 tests；覆盖词法链接过滤、GitHub-compatible Markdown 锚点、Setext/CJK/emoji/HTML 自定义锚点、嵌套 frontmatter、解析错误、扩展敏感模式、项目白名单、中英文占位符、根目录 Markdown 排除、图片与引用定义、配置、双向导航、元数据关系、阶段门、重复 finding 去重、Agent 评测证据校验、机器规则双向绑定、结构化 trace 与 evidence 交叉校验、condition-aware paired delta、required/allowed/forbidden reads、benchmark 聚合、naturalistic 独立 grader、capture runner、自然任务聚合、审计性能夹具、中英文 README 文档路由、决策笔记生命周期/关系校验、supersedes 目标/链接/环检查和归档预览/应用 |
| Agent 评测证据 CLI | `python skills/r-doc/scripts/evaluate_agent.py --cases skills/r-doc/evals/cases.json --input skills/r-doc/evals/example-evidence.json --strict --json` | PASS，完整证据示例覆盖八个场景，分离 `paths_checked`/`files_read`，按 `machine_rules` 推导机器维度，验证必需命令的退出码与顺序，并绑定精确 `skill_version`；工具只校验外部 Agent 证据，不伪造模型轨迹 |
| 官方 Skill creator 校验 | `PYTHONUTF8=1 python <skill-creator>/scripts/quick_validate.py skills/r-doc`（PowerShell 先设置 `$env:PYTHONUTF8='1'`） | PASS，官方校验器通过 |
| 本地 npx skills 发现 | `npx skills add . --list` | PASS，发现 1 个 r-doc |
| Agent benchmark 聚合器 | `python skills/r-doc/scripts/aggregate_benchmarks.py --root benchmarks --write-results` | PASS，当前状态为 `partial`；summary 明确标为 `skill-layer-ablation`，3 组配对仅 trend-ready，未把 naturalistic 记录混入 conformance |
| Naturalistic independent grader | `python benchmarks/naturalistic/aggregate.py --root benchmarks/naturalistic-runs`；Luna 批次另以 `--root benchmarks/naturalistic-runs-20260919-luna` 聚合 | PASS；既有正式根目录仍为 4 个任务各 1 对的 `gpt-5.5` 基线。用户确认并扩展的 `gpt-5.6-luna` 聚合 summary 共记录 80 次 measurement-valid 运行、40 个 paired comparisons，4 个任务各 10 对，`coverage_pair_count=40`、`replicated_task_count=4`、`min_pairs_per_task=10`，全部达到 strong-evidence 样本量门槛；本地运行的 80/80 artifact/hash integrity 通过。该批次仍只有一个模型，76/80 运行因 forbidden reads 失败，两个条件的 task_success/context_safety 均为 5%，因此不构成正向 effectiveness 结论；原始 trace/log 因机器路径未进入公开提交 |
| 审计性能基线 | `python skills/r-doc/scripts/benchmark_audit.py --sizes 100,1000,5000 --iterations 10 --output benchmarks/performance-baseline.json` | PASS，默认记录 10 次本机中位数、插值 p95、最大值、低样本标记、Python 和平台信息；不作为 CI 硬门槛 |
| 工作树空白错误 | `git diff --check` | PASS |
| 源副本同步 | 将 `skills/r-doc/` 同步到全局运行副本并比较关键文件 SHA-256 | PASS，关键源文件与运行副本一致 |

## 嵌套 frontmatter dogfood

本记录自身的 `validation` 字段使用嵌套映射和列表，作为仓库真实文档对 YAML frontmatter 解析能力的 dogfood 样例。严格审计会读取并保留以下结构，而不是把它降级为扁平键值：

```yaml
validation:
  parser: PyYAML BaseLoader
  scenarios:
    - nested-mapping
    - nested-list
```

## 覆盖的临时项目场景

- 入口和嵌套索引完整时严格审计通过；
- 缺少根 `AGENTS.md` 时报告入口错误；
- 断链时报告目标和行号；
- 未被索引的主题文档时报告覆盖缺口；
- 检测到疑似密钥时报告敏感内容；
- 发现重复文档 ID 时报告冲突。
- 预览不会写入文件；显式应用后可重复运行且不再产生修复；
- 缺失索引链接会被补入；并发修改会被拒绝，避免覆盖新内容。
- 自定义文档根目录和排除目录会生效；重复或非法配置会失败；
- 根入口、文档总索引和嵌套索引的双向导航会被检查；
- 引用式、带括号和逃逸项目根目录的链接会被确定性解析和报告；
- `related_docs`、`supersedes`、标题一致性、日期顺序和类型关系会被检查。
- 同一路径和同一错误的重复 finding 会被合并，减少多阶段读取不可用文件时的输出噪声。
- 根目录直接维护的 Markdown 会参与断链和敏感值检查；图片目标会检查存在性但不会改变导航覆盖图。
- `related_code` 必须指向项目根目录内的现有文件；`status: superseded` 必须有声明 `supersedes` 的替代文档，并由旧文档正文回链。
- 决策笔记会检查生命周期/分类路径、必需章节、`supersedes` 目标与回链、自引用、环引用和归档日期；归档命令默认只预览，只有显式 `--apply` 才移动文件，并拒绝冲突或并发修改。
- 未配置的 `--stage` 会报告 `invalid-stage` 并以失败退出；未使用的引用定义不会伪造文档可达性。
- fenced code、行内代码和 HTML 注释中的链接语法不会被当作真实链接；Markdown fragment 会校验目标文档中的标题锚点。
- 标题锚点按 GitHub-compatible 规则覆盖 ATX/Setext、CJK、标点、连续空格、重复标题后缀及 `<a name>`/`<a id>` 自定义锚点；其他渲染器专有 slug 不自动推断。
- 标题 slug 保留 emoji 码点，并由回归场景验证 `#deploy-🚀` 这类 fragment。
- 根目录 `README.md` 默认参与审计，`.r-doc.yaml` 的 `exclude` 同样可以排除根目录 Markdown，但不会排除 `AGENTS.md`。
- `planned_code` 可以指向尚未创建但仍在项目根目录内的未来路径；`related_code` 仍必须指向现有文件。
- `sensitive_allowlist` 可以为受支持检测器登记精确的官方示例值，命中会保留 informational finding，非法检测器配置会失败。
- 测试按 `test_audit_docs.py`、`test_config_and_sensitive.py`、`test_repair_docs.py`、`test_agent_evaluation.py`、`test_benchmark_tools.py`、`test_decision_notes.py`、`test_decision_note_cli.py` 和 `test_rdoc_modules.py` 拆分，便于按责任域定位回归。
- `evals/example-evidence.json` 是可直接通过评测器的完整八场景证据样例，`cases.json` 的 `machine_rules` 明确声明机器维度的输入检查和通过条件。
- `scripts/rdoc/` 统一提供配置、finding、安全检测、Markdown 解析和锚点生成；审计、修复、包校验和 Agent 评测不再从 `audit_docs.py` 交叉导入共享逻辑。
- `evals/cases.json` 与 `evaluate_agent.py` 将 Agent 行为评测的证据结构、八个场景完整性和可比评分变成可执行检查；仍需由真实 Agent 产生 prompt、读取清单、diff 和报告。
- `machine_rules` 的规则标识、代码实现注册表和 cases.json 做双向一致性校验；改名或漏绑定会在加载 cases 时失败。
- `benchmarks/summary.json` 当前为 `partial`，并机器可读地标注 `skill-layer-ablation`、`case-contract` activation 和 `agent-generated` review；真实 Codex 与 `baseline-no-r-doc` 运行必须分别保存 manifest 绑定的结构化 `trace.jsonl`、`evidence.json`，再由聚合器从 trace 交叉验证 evidence 并生成 `result.json` 与配对 delta；旧的一行占位 trace 不再通过。
- `benchmarks/naturalistic/` 定义不泄露 activation/read/command 答案的第二层协议；独立 grader 只读取任务规格、最终状态和 action trace，不读取 Agent 自评；模型选择必须先获得用户确认并原样写入 manifest；当前正式基线保存在 `benchmarks/naturalistic-runs/summary.json`，用户确认的 Luna 聚合 summary 保存在 `benchmarks/naturalistic-runs-20260919-luna/summary.json`，两者都明确区分负向安全观测与正向 effectiveness 结论；Luna 原始 trace/log 因含机器路径留在本地。
- `benchmark_audit.py` 对 100、1000、5000 个 Markdown 文档夹具记录审计耗时，性能数值只用于本机规模趋势。

## 限制

这份记录证明当前源副本和确定性验证路径可复现，不等同于真实外部项目的长期采用数据。Conformance benchmark 的 Agent 评测入口能校验证据完整性，但不会替代 naturalistic 独立评分或跨模型真实运行；当前 skill-layer 汇总仍为 `partial`，Luna naturalistic 汇总已达到 strong-evidence 样本量门槛但仍是单模型观测。Luna 批次 80 次运行中有 76 次 forbidden-read 失败，两个条件的 task_success/context_safety 均为 5%，尚无正向 effectiveness 结论；后续如需加入第二模型，必须先重新获得用户确认。

返回：[开发文档索引](README.md) · [文档总索引](../README.md)

## English verification summary

This record captures reproducible checks for the current source copy. Commands run from the repository root are read-only unless explicitly stated.

| Check | Result |
| --- | --- |
| Skill package validation | PASS |
| Repair preview | PASS; no safe writes pending |
| Strict documentation audit | PASS; 0 errors and 0 warnings |
| Unit and temporary-project suite | PASS; 116 tests, including structured trace/evidence validation, paired aggregation, naturalistic independent grading, capture runner, naturalistic aggregation, bilingual public-document routing, decision-note lifecycle/relationship checks, supersession graph checks, and archive preview/application |
| Agent-evidence CLI | PASS; complete eight-scenario example and exact Skill-version binding |
| Official Skill Creator validator | PASS; the official `quick_validate.py` check succeeds |
| Benchmark aggregation | PASS; conformance `partial` with three trend-ready pairs; official naturalistic baseline remains four single-pair tasks, while the approved Luna batch separately reports 40 matched pairs across four tasks and reaches the strong-evidence sample-size threshold |
| Naturalistic capture and grading | PASS; the approved `gpt-5.6-luna` aggregate records 80 measurement-valid runs, 40 complete paired comparisons, ten pairs per task, and local 80/80 artifact-integrity passes; 76 forbidden-read failures remain visible as measured negative safety outcomes, with 5% task-success/context-safety averages in both conditions. Raw machine-path-bearing traces/logs are not part of the public commit |
| Diff whitespace check | PASS |
| Source/runtime-copy synchronization | PASS; key source files have matching SHA-256 hashes in the global runtime copy |

The official naturalistic baseline remains preliminary, while the approved Luna batch has ten paired repetitions per task and strong-evidence sample-size readiness but no second model and weak context-safe coverage. These results still do not establish positive product effectiveness: 76 of 80 Luna runs failed forbidden-read checks and both conditions averaged 5% task success/context safety. Any new model or repetition batch requires explicit user confirmation before capture. The conformance score proves trace/evidence structure and protocol execution, not natural activation or independent task effectiveness.

Back to: [development index](README.md) · [documentation index](../README.md)
