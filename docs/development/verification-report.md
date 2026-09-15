---
id: VERIFICATION-RDOC-001
type: report
status: active
title: r-doc 可复现验证记录
created: 2026-09-14
updated: 2026-09-15
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
| 临时项目行为场景 | `python -m unittest discover -s skills/r-doc/tests -p 'test_*.py'` | PASS，68 tests；覆盖词法链接过滤、GitHub-compatible Markdown 锚点、Setext/CJK/emoji/HTML 自定义锚点、嵌套 frontmatter、解析错误、扩展敏感模式、项目白名单、中英文占位符、根目录 Markdown 排除、图片与引用定义、配置、双向导航、元数据关系、阶段门、重复 finding 去重、Agent 评测证据校验、机器规则双向绑定、benchmark 聚合、审计性能夹具和中英文 README 文档路由 |
| Agent 评测证据 CLI | `python skills/r-doc/scripts/evaluate_agent.py --cases skills/r-doc/evals/cases.json --input skills/r-doc/evals/example-evidence.json --strict --json` | PASS，完整证据示例覆盖八个场景，分离 `paths_checked`/`files_read`，按 `machine_rules` 推导机器维度，验证必需命令的退出码与顺序，并绑定精确 `skill_version`；工具只校验外部 Agent 证据，不伪造模型轨迹 |
| 官方 Skill creator 校验 | `PYTHONUTF8=1 python <skill-creator>/scripts/quick_validate.py skills/r-doc`（PowerShell 先设置 `$env:PYTHONUTF8='1'`） | PASS |
| 本地 npx skills 发现 | `npx skills add . --list` | PASS，发现 1 个 r-doc |
| Agent benchmark 聚合器 | `python skills/r-doc/scripts/aggregate_benchmarks.py --root benchmarks` | PASS，当前状态为 `pending`；没有真实 Agent run 时不生成虚假分数 |
| 审计性能基线 | `python skills/r-doc/scripts/benchmark_audit.py --sizes 100,1000,5000 --iterations 3 --output benchmarks/performance-baseline.json` | PASS，记录本机中位数、p95、Python 和平台信息；不作为 CI 硬门槛 |
| 工作树空白错误 | `git diff --check` | PASS |

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
- 未配置的 `--stage` 会报告 `invalid-stage` 并以失败退出；未使用的引用定义不会伪造文档可达性。
- fenced code、行内代码和 HTML 注释中的链接语法不会被当作真实链接；Markdown fragment 会校验目标文档中的标题锚点。
- 标题锚点按 GitHub-compatible 规则覆盖 ATX/Setext、CJK、标点、连续空格、重复标题后缀及 `<a name>`/`<a id>` 自定义锚点；其他渲染器专有 slug 不自动推断。
- 标题 slug 保留 emoji 码点，并由回归场景验证 `#deploy-🚀` 这类 fragment。
- 根目录 `README.md` 默认参与审计，`.r-doc.yaml` 的 `exclude` 同样可以排除根目录 Markdown，但不会排除 `AGENTS.md`。
- `planned_code` 可以指向尚未创建但仍在项目根目录内的未来路径；`related_code` 仍必须指向现有文件。
- `sensitive_allowlist` 可以为受支持检测器登记精确的官方示例值，命中会保留 informational finding，非法检测器配置会失败。
- 测试按 `test_audit_docs.py`、`test_config_and_sensitive.py`、`test_repair_docs.py`、`test_agent_evaluation.py`、`test_benchmark_tools.py` 和 `test_rdoc_modules.py` 拆分，便于按责任域定位回归。
- `evals/example-evidence.json` 是可直接通过评测器的完整八场景证据样例，`cases.json` 的 `machine_rules` 明确声明机器维度的输入检查和通过条件。
- `scripts/rdoc/` 统一提供配置、finding、安全检测、Markdown 解析和锚点生成；审计、修复、包校验和 Agent 评测不再从 `audit_docs.py` 交叉导入共享逻辑。
- `evals/cases.json` 与 `evaluate_agent.py` 将 Agent 行为评测的证据结构、八个场景完整性和可比评分变成可执行检查；仍需由真实 Agent 产生 prompt、读取清单、diff 和报告。
- `machine_rules` 的规则标识、代码实现注册表和 cases.json 做双向一致性校验；改名或漏绑定会在加载 cases 时失败。
- `benchmarks/summary.json` 当前保持 `pending`，真实 Codex 与 `baseline-no-r-doc` 运行必须分别保存 `run.json`、实际 `trace.jsonl`、`evidence.json`，再由聚合器生成 `result.json`。
- `benchmark_audit.py` 对 100、1000、5000 个 Markdown 文档夹具记录审计耗时，性能数值只用于本机规模趋势。

## 限制

这份记录证明当前源副本和确定性验证路径可复现，不等同于真实外部项目的长期采用数据。Agent 评测入口能校验证据完整性，但不会替代跨模型真实运行；当前 benchmark 汇总仍为 `pending`。发布后应继续补充来自真实项目的匿名化验证记录和兼容性反馈。

返回：[开发文档索引](README.md) · [文档总索引](../README.md)
