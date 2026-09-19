# Changelog

This file records user-visible changes to r-doc.

## Unreleased

- 发布规范明确 GitHub Release 必须通过本机 Git Credential Manager 和 GitHub REST API 创建/上传，按 tag 幂等检查并回读验证；浏览器仅可用于只读查看公开结果。

### English

- Release governance now requires GitHub Releases to be created and uploaded through the local Git Credential Manager and GitHub REST API, with idempotent tag checks and API read-back verification; the browser is read-only for checking the public result.

## [0.3.0] - 2026-09-19

- Corrected naturalistic measurement semantics: the CLI task no longer forbids the `user_name` identifier inside a valid negative-option test, and command-level read inference now distinguishes `rg` hidden-file/content-search behavior from `rg --files`, `Get-ChildItem`, and `git status` metadata operations.
- Reworked naturalistic coverage reporting so total pair coverage is separate from per-task replication and readiness; checked-in traces and results were replayed from raw CLI events, and text artifact hashes are stable across LF/CRLF checkouts.
- Added an explicit benchmark governance gate: model selection for real Agent/test-data capture requires the user's confirmation before any new run batch, and confirmed models must be recorded without silent mixing across experiments.
- Added an optional decision-note layer with lifecycle/class routing, deterministic validation, project configuration, a reusable template, and tests; existing projects remain compatible when no notes root is present.
- Added supersession target/link/cycle checks and a safe decision-note archive helper with preview-by-default and explicit `--apply` mutation.

### 中文摘要

- 修正 naturalistic 测量语义：CLI 任务不再禁止合法的旧参数拒绝测试中出现 `user_name` 标识符；命令级读取推断区分 `rg` 的 hidden/内容搜索语义，以及 `rg --files`、`Get-ChildItem` 和 `git status` 的元数据操作。
- 重做 naturalistic coverage 报告，将总配对覆盖与每任务重复/就绪度分开；已从原始 CLI 事件重放仓库内 trace/result，并让文本 artifact hash 兼容 LF/CRLF checkout。
- 增加 benchmark 治理门禁：真实 Agent/测试数据采集涉及的模型选择必须先获得用户确认，确认后的模型必须原样记录，不能在实验批次之间静默混用。
- 增加可选的决策笔记层，支持生命周期/分类路径、确定性校验、项目配置、复用模板和测试；未创建笔记根目录的现有项目保持兼容。
- 增加 supersedes 目标/链接/环检查和安全的决策笔记归档辅助命令，默认只预览，只有显式 `--apply` 才执行移动。

This release is backward-compatible for projects that do not configure a decision-note root. The naturalistic benchmark extension is measurement evidence only: it reaches the sample-size threshold but does not establish positive effectiveness.

The public repository includes the Luna aggregate summary; raw local CLI traces and logs remain outside the release because they contain machine-specific paths.

## [0.2.17] - 2026-09-15

- Completed the naturalistic capture boundary: the runner builds isolated fixtures, invokes the agent with only the user task, independently snapshots the final workspace, normalizes the raw CLI trace, hashes capture artifacts, and invokes the independent grader.
- Added grader-owned executable outcome checks for pytest, callable behavior, and documentation assertions; hardened Windows path normalization and rejected cross-layer naturalistic runs at the conformance aggregator entrypoint.
- Added four naturalistic task specifications and a separate multi-run aggregator that reports matched-pair readiness, task diversity, and multi-model coverage. Captured and independently graded four real matched pairs across the four tasks with Codex `gpt-5.5`; the aggregate is `partial` and all eight runs currently fail context safety on forbidden `.env`/`secrets.md` reads, so no positive effectiveness claim is made.

### 中文摘要

- 补完整 naturalistic capture 边界：runner 构建隔离 fixture，只向 Agent 发送用户任务，独立读取最终 workspace、规范化原始 CLI trace、哈希捕获产物，并调用独立 grader。
- 增加 grader 自己执行的 pytest、callable 行为和文档断言；修复 Windows 路径规范化侧门，并让 conformance 聚合器在入口拒绝误标的 naturalistic run。
- 增加四个自然任务和独立多运行聚合器，报告配对 readiness、任务多样性和多模型覆盖；已经完成四个任务各一对、共 8 次 `gpt-5.5` 真实 capture，聚合为 `partial`，但全部因读取 `.env`/`secrets.md` 而 context safety 失败，因此不宣称正向 naturalistic effectiveness result。

## [0.2.16] - 2026-09-15

- Reclassified the fixed-prompt benchmark as a Conformance Benchmark and `skill-layer-ablation`; its activation metric is protocol compliance against disclosed case answers, and its review dimensions are explicitly agent-generated.
- Added machine-readable benchmark-layer, prompt-contract, activation-ground-truth, grader, and review-provenance metadata to real-run manifests and aggregate summaries.
- Added the Naturalistic Effectiveness Benchmark protocol and an independent final-state/trace grader without claiming results before matched real captures exist.
- Enabled protected `main` governance with pull-request review and no force-push/deletion; the local GPG signing probe passes, while existing v0.2.15 history remains unchanged because it is already public and unsigned. The next release must still be verified as `Verified` on GitHub.

### 中文摘要

- 将固定 prompt benchmark 明确归类为 Conformance Benchmark / `skill-layer-ablation`；activation 衡量协议遵循，review 维度明确来自 Agent 自评。
- 为运行记录和聚合结果增加 benchmark 层、prompt 契约、activation ground truth、grader 和 review provenance 元数据。
- 增加 Naturalistic Effectiveness Benchmark 协议与独立的最终状态/trace grader；在匹配的真实运行捕获前不宣称结果。
- 已启用 `main` 分支保护。本机 GPG 签名探针通过，但公开的 v0.2.15 历史保持 unsigned、不重写；下一版仍需在 GitHub 验证为 `Verified`。

## [0.2.15] - 2026-09-15

- Upgraded the evidence schema to version 3 and required the trace to independently record `prompt`, `activation_decision`, `skill_selected`, `governance_report`, `final_response`, `diff_snapshot`, and human review; the aggregator derives and cross-validates these fields from the trace.
- Upgraded the trace schema to version 2 and rejected undeclared fields by event type; forbidden reads now lower `context_economy` in normal evaluation and fail under `--strict` and benchmark aggregation gates.
- Added trend, statistical, and strong-evidence sample thresholds for paired deltas, with 95% Student-t confidence intervals; added real Codex benchmark capture records and run instructions.
- Clarified the boundary between `condition` and Skill selection: the baseline still judges activation by scenario, and code-only scenarios select no r-doc Skill under either condition; failed real captures remain available for audit but are excluded from aggregation, and Windows CLI output is forced to UTF-8 for CJK and emoji traces.

### 中文摘要

- 将 evidence schema 升级到 v3，并要求 trace 独立记录 prompt、activation、skill、报告、最终响应、diff 和 review，再由聚合器交叉校验。
- 将 trace schema 升级到 v2，按事件类型拒绝未声明字段；forbidden read 在普通评估中降低 context economy，在 strict 和聚合门禁中失败。
- 增加配对 delta 的 trend/statistical/strong-evidence 样本门槛、95% Student-t 区间，以及真实 Codex 捕获记录和运行说明。
- 澄清 condition 与 Skill 选择的边界，保留失败 capture 供审计但排除出聚合，并强制 Windows CLI 使用 UTF-8 保存 CJK/emoji trace。

## [0.2.14] - 2026-09-15

- Upgraded real Agent benchmark traces to structured JSONL with run-metadata binding, scenario lifecycle, and action events, and cross-validated path, read, command, and write evidence from the trace.
- Added paired `with-r-doc`/`baseline-no-r-doc` deltas keyed by `agent + model + run_id`, together with mean, median, standard deviation, and statistical readiness; profile summaries no longer mix conditions.
- Split context-economy read policy into required, allowed, and forbidden sets, reporting unnecessary, forbidden, and missing-required reads separately.
- Raised the default audit performance baseline to 10 iterations and recorded linearly interpolated p95, maximum values, and low-sample notices.

### 中文摘要

- 将真实 Agent benchmark trace 升级为带运行元数据绑定、场景生命周期和 action 事件的结构化 JSONL，并从 trace 交叉验证路径、读取、命令和写入证据。
- 按 `agent + model + run_id` 输出 `with-r-doc` 与 `baseline-no-r-doc` 配对 delta，并提供均值、中位数、标准差和统计就绪度；profile 不再混合 condition。
- 将 context-economy 读取策略拆为 required、allowed、forbidden，分别报告 unnecessary、forbidden 和 missing-required reads。
- 审计性能基线默认提升到 10 次迭代，并记录插值 p95、最大值和低样本提示。

## [0.2.13] - 2026-09-15

- Added paired Chinese and English security-fix, practical-example, and common-pitfall reference documents for the GitHub public entrypoints; the Chinese README no longer routes users to English guides.
- Added Chinese backlinks for canonical English references and changed the Chinese Skill reference entrypoint to language-consistent document routes.
- Added public-document language-routing regression tests to prevent README links from drifting again.

### 中文摘要

- 为 GitHub 公开入口增加安全修复、实际案例和常见避坑指南的中英文配对文档，并让中文 README 指向中文指南。
- 为 canonical English references 增加中文回链，并让中文 Skill 参考入口使用一致的语言路由。
- 增加公开文档语言路由回归测试，防止 README 链接再次漂移。

## [0.2.12] - 2026-09-15

- Added the real Agent benchmark directory contract, run-evidence aggregator, and baseline notes without presenting example evidence as real results.
- Added bidirectional consistency checks for `machine_rules` identifiers, the code registry, and `cases.json` to prevent rule-name drift.
- Added an audit performance baseline tool for 100, 1,000, and 5,000 Markdown documents, together with the first local measurement record.

### 中文摘要

- 增加真实 Agent benchmark 目录契约、运行 evidence 聚合器和 baseline 说明，不把示例 evidence 当作真实结果。
- 增加 `machine_rules` 标识、代码注册表和 `cases.json` 的双向一致性检查，防止规则名称漂移。
- 增加针对 100、1,000、5,000 个 Markdown 文档的审计性能基线工具及首份本机测量记录。

## [0.2.11] - 2026-09-15

- Added a complete Agent evidence example that can pass the evaluator directly, preventing documentation fragments from drifting away from the actual schema.
- Moved machine-dimension derivation rules into `machine_rules` in `evals/cases.json`; the evaluator now checks and reports them, making each dimension's inputs and pass conditions explicit.
- Added regression coverage for the complete evidence example so it cannot fall behind the implementation again.

### 中文摘要

- 增加可直接通过评测器的完整 Agent evidence 示例，避免文档片段与实际 schema 脱节。
- 将机器维度推导规则移入 `evals/cases.json` 的 `machine_rules`，并由评测器校验和报告，使输入与通过条件显式化。
- 增加完整 evidence 示例的回归测试，防止示例再次落后于实现。

## [0.2.10] - 2026-09-15

- Separated `paths_checked` from `files_read` in Agent evaluation evidence so checking a nonexistent path is not misreported as reading its contents.
- Changed required commands to an ordered success sequence and validated command names, integer exit codes, and declared order.
- Split scoring into evidence-derived machine checks and evidence-backed human review, reducing unsupported self-reported scores.
- Added regression tests for the shared `rdoc` modules; this version contains 59 regression tests.

### 中文摘要

- 将 `paths_checked` 与 `files_read` 分离，避免把不存在路径的检查误记成内容读取。
- 将必需命令改为有序成功序列，验证命令名、整数退出码和声明顺序。
- 将评分拆为从 evidence 推导的机器检查和有证据支撑的人工复核，减少无依据的自报分数。
- 为共享 `rdoc` 模块增加回归测试；本版包含 59 个回归测试。

## [0.2.9] - 2026-09-15

- Removed the top-level eager re-export from the `rdoc` package; audit, repair, and package-validation tools now import direct submodules, reducing package-initialization coupling.
- Added and enforced `skill_version` validation for Agent evaluation cases and evidence so cross-version results can be labeled and compared accurately.
- Added the 0.2.9 migration matrix and verification documentation; the regression suite grew to 51 tests.

### 中文摘要

- 移除 `rdoc` 顶层 eager re-export，让审计、修复和包校验工具直接导入所需子模块，降低初始化耦合。
- 强制 Agent 评测 cases/evidence 校验 `skill_version`，使跨版本结果可以准确标记和比较。
- 增加 0.2.9 迁移矩阵和验证文档；回归测试增至 51 个。

## [0.2.8] - 2026-09-15

- Moved configuration loading, finding models, sensitive-value detection, Markdown target parsing, and heading-anchor generation into the shared `scripts/rdoc/` package for reuse by audit, repair, package validation, and Agent evaluation, reducing single-file responsibilities and import coupling.
- Expanded Agent evaluation from 5 to 8 scenarios, adding configuration-driven governance, superseded-document closure, and Markdown-anchor validation scenarios, with the evidence contract updated accordingly.
- Corrected emoji handling in heading slugs, preserving emoji code points and adding GitHub-compatible anchor regression tests.
- Kept all 50 regression tests passing and updated the verification, migration, and public documentation.

### 中文摘要

- 将配置、安全检测、Markdown 解析和锚点生成下沉到共享 `scripts/rdoc/`，供审计、修复、包校验和 Agent 评测复用。
- 将 Agent 评测从 5 个场景扩展到 8 个，增加配置驱动治理、superseded 文档闭环和 Markdown 锚点场景，并同步 evidence 契约。
- 修正标题 slug 的 emoji 处理，保留 emoji 码点并增加 GitHub-compatible 锚点回归测试。
- 保持 50 个回归测试通过，并同步验证、迁移和公开文档。

## [0.2.7] - 2026-09-15

- Expanded Markdown-anchor validation to GitHub-compatible ATX and Setext headings, CJK text, consecutive-space and punctuation boundaries, duplicate-heading suffixes, and explicit HTML `name`/`id` anchors, with matching regression tests.
- Kept `sensitive_allowlist` matches as informational findings and added a complete matrix for eight project-configuration fields, frontmatter ownership guidance for `planned_code`, and root-level `exclude` test evidence.
- Added a cross-version migration overview and executable Agent-evidence validator, documenting the upgrade strategy for patch releases that may add audit findings.
- Expanded temporary-project regression tests to 50 and passed the Skill-package, official Skill Creator, repair-preview, and strict-audit gates.

### 中文摘要

- 扩展 Markdown 锚点校验，覆盖 GitHub-compatible ATX/Setext 标题、CJK、连续空格、标点、重复标题后缀和 HTML `name`/`id` 锚点。
- 保留 `sensitive_allowlist` 命中的 informational finding，并补充项目配置矩阵、`planned_code` frontmatter 归属说明和根目录 `exclude` 证据。
- 增加跨版本迁移总览和可执行 Agent-evidence validator，记录可能增加审计 finding 的 patch 升级策略。
- 临时项目回归测试扩展至 50 个，并通过 Skill 包、官方 Skill Creator、修复预览和严格审计门禁。

## [0.2.6] - 2026-09-15

- Made Markdown link parsing ignore fenced code, inline code, and HTML comments while continuing to scan sensitive values in fenced code; added Markdown fragment and anchor-existence validation.
- Added the `sensitive_allowlist` project configuration as a reviewed exact-example extension point for each detector, together with baseline detection for Google `AIza`-style API keys.
- Clarified root-level Markdown `exclude` behavior: `README.md` is included by default, configured exclusions also apply to root Markdown files, and `AGENTS.md` is always checked as an entrypoint.
- Added the `planned_code` metadata field for planned code paths that do not yet exist but must remain inside the project root, while preserving the existing-file requirement for `related_code`.
- Split temporary-project tests into focused audit-core, configuration/sensitive-value, and repairer modules while keeping 45 independently locatable regression scenarios.

### 中文摘要

- 让 Markdown 链接解析忽略 fenced code、行内代码和 HTML 注释，同时继续扫描 fenced code 中的敏感值，并增加 fragment/anchor 存在性验证。
- 增加 `sensitive_allowlist` 精确示例扩展点和 Google `AIza` 风格 API key 基线检测。
- 澄清根目录 Markdown 的 `exclude` 行为，并增加 `planned_code` 记录尚未创建但受根目录约束的未来路径。
- 将临时项目测试拆为审计核心、配置/敏感值和修复器模块，保留 45 个可独立定位的回归场景。

## [0.2.5] - 2026-09-14

- Included directly maintained Markdown files in the project root in broken-link and sensitive-value audits, covering high-risk entrypoints such as README, contribution guides, and security notes; document metadata and index coverage remain limited to the configured `docs_root`.
- Made image links participate in target-existence checks without adding images or unused reference definitions to the documentation graph; nested indexes and their direct parent/child indexes must also be reachable in both directions.
- Added replacement-document relationships and body backlinks for `status: superseded`, existing-file validation for `related_code`, and immediate failure for an unconfigured `--stage`.
- Added an exact allowlist entry for the official public AWS example `AKIAIOSFODNN7EXAMPLE` while retaining sensitive-value scanning for other code-block content, avoiding a leakage blind spot under the label of “example code.”

### 中文摘要

- 将根目录维护的 Markdown 纳入断链和敏感值审计，同时把元数据和索引覆盖限定在配置的 `docs_root`。
- 让图片链接参与目标存在性检查，但不把图片或未使用引用定义加入文档导航图；嵌套索引必须与直接父/子索引双向可达。
- 增加 replacement-document 关系、`status: superseded` 正文回链、`related_code` 现有文件校验，并对未配置的 `--stage` 立即失败。
- 精确允许官方 AWS 公开示例值，同时继续扫描其他代码块中的敏感值，避免以“示例代码”为名形成盲区。

## [0.2.4] - 2026-09-14

- Deduplicated repeated audit findings with the same path, finding type, message, and line number, reducing noise when symlinks or unreadable files are read by multiple check phases.
- Added migration guidance for existing 0.2.3 projects, covering bidirectional navigation, repair previews, and strict review steps.
- Added a deterministic coverage matrix for configuration, navigation, links, metadata relationships, and sensitive content to the verification documentation, together with evidence for 27 regression tests.

### 中文摘要

- 对重复路径、finding 类型、消息和行号完全相同的审计 finding 去重，降低多阶段读取产生的噪声。
- 增加 0.2.3 存量项目迁移指南，覆盖双向导航、修复预览和严格审阅步骤。
- 在验证文档中加入配置、导航、链接、元数据关系和敏感内容的确定性覆盖矩阵，并记录 27 个回归测试证据。

## [0.2.3] - 2026-09-14

- Made `.r-doc.yaml`, `docs/r-doc.yaml`, and `r-doc.yaml` drive the documentation root, exclusions, required document types, relationship requirements, and stage gates; duplicate or invalid configuration now becomes an audit error.
- Turned bidirectional entrypoint/index navigation, nested-index backlinks, and index coverage into deterministic audit rules; the repairer reuses the same configuration and fills navigation with one atomic update.
- Added support for reference-style Markdown links and parenthesized link targets, and checked resolved paths against the project-root boundary, including symlink-escape risks.
- Validated `related_docs`, `supersedes`, `review_after`, `related_code`, the title and first H1, creation/update ordering, and configured document-type relationships.
- Expanded temporary-project regression scenarios from 18 to 26, covering configuration, navigation, link parsing, metadata relationships, and stage gates.

### 中文摘要

- 让 `.r-doc.yaml`、`docs/r-doc.yaml` 和 `r-doc.yaml` 驱动文档根目录、排除项、必需类型、关系要求和阶段门；重复或非法配置现在会成为审计错误。
- 将入口/索引双向导航、嵌套索引回链和索引覆盖变成确定性规则，修复器复用同一配置并以原子更新补齐导航。
- 增加引用式和带括号的 Markdown 链接，检查解析后路径是否越出项目根目录，并校验 `related_docs`、`supersedes`、`review_after`、`related_code`、标题及日期顺序。
- 临时项目回归场景从 18 个扩展到 26 个，覆盖配置、导航、链接解析、元数据关系和阶段门。

## [0.2.2] - 2026-09-14

- Expanded the generic password-placeholder allowlist to include Chinese forms such as `你的密码`, `请输入你的密码`, `示例口令`, and `待填写`, and added regression coverage for real Chinese passwords.
- Added nested mappings and lists in frontmatter to the repository's own verification record as dogfood evidence for parser support.

### 中文摘要

- 扩展通用密码占位符白名单，识别 `你的密码`、`请输入你的密码`、`示例口令`、`待填写` 等中文形式，并增加真实中文密码回归覆盖。
- 在仓库自身验证记录中使用 frontmatter 嵌套映射和列表，作为解析器支持能力的 dogfood 证据。

## [0.2.1] - 2026-09-14

- Used PyYAML safe parsing for frontmatter, supporting nested mappings and lists; malformed YAML is reported explicitly instead of silently dropping fields.
- Removed the ineffective `strict` branch from audit functions, leaving warning thresholds to the command-line entrypoint.
- Expanded the sensitive-information baseline to JWTs, OpenAI API keys, credentialed database connection strings, and generic password assignments, while documenting coverage and known limitations.
- Added regression tests for frontmatter, parse failures, and new sensitive patterns.
- Expanded GitHub Actions to an Ubuntu/Windows and Python 3.10–3.13 matrix, with the PyYAML development dependency pinned.

### 中文摘要

- 使用安全 YAML 解析处理嵌套 frontmatter，并显式报告 malformed YAML，而不是静默丢弃字段。
- 将敏感信息基线扩展到 JWT、OpenAI API key、带凭据数据库连接串和通用密码赋值，同时记录覆盖边界。
- 增加回归测试，并将 GitHub Actions 扩展到 Ubuntu/Windows 与 Python 3.10–3.13 矩阵，固定 PyYAML 开发依赖版本。

## [0.2.0] - 2026-09-14

- Improved the `SKILL.md` discovery description and OpenAI UI short description with project-documentation governance, document-consistency, and change-tracking trigger terms.
- Added a skills.sh badge, quick-install section, and common-request entry table above the fold in the README.
- Made the English README the default global entrypoint while retaining `README.zh-CN.md` as the Chinese mirror with a language switch link.
- Translated the runtime `SKILL.md` into English while retaining `SKILL.zh-CN.md` as a Chinese explanatory mirror for global discovery and use.
- Rewrote the README's core principles, differentiators, and development-lifecycle governance guidance.
- Corrected GitHub and `npx skills` installation examples, clarifying the distinction between the repository source `riesaexe/r-doc` and the Skill name `r-doc`.
- Standardized runtime references and templates on English, and narrowed `SKILL.zh-CN.md` to a Chinese pointer for human maintainers to avoid a second drifting set of runtime rules.
- Added `audit_docs.py`, `validate_skill.py`, temporary-project unit tests, and GitHub Actions quality gates, reducing reliance on model self-discipline for verification.
- Added an `AGENTS.md` template, practical usage examples, and troubleshooting entrypoints covering core artifacts and the getting-started path.
- Tightened implicit activation boundaries so a purely code-only local change with no documentation impact does not start the full governance workflow.
- Removed personal machine paths from project documentation and replaced them with portable path expressions.
- Added a read-only-by-default safe-repair mode to `repair_docs.py`; only explicit `--apply` fills entrypoints, indexes, and missing links, while refusing to overwrite, delete, or resolve conflicts by guesswork.
- Added practical examples for initialization, interface changes, release audits, and topic directories, together with a centralized pitfalls and safeguards guide.

### 中文摘要

- 改善 `SKILL.md` 发现描述和 OpenAI UI 短描述，加入项目文档治理、一致性和变更追踪触发词。
- 为 README 增加 skills.sh 徽章、快速安装和常见请求入口，并明确 GitHub 仓库来源与 Skill 名称的区别。
- 将运行时 `SKILL.md` 统一为英语，同时保留 `SKILL.zh-CN.md` 作为中文解释入口；参考文档和模板采用英语 canonical 版本。
- 增加 `audit_docs.py`、`validate_skill.py`、临时项目测试和 GitHub Actions 质量门禁，减少对模型自律的依赖。
- 增加 AGENTS 模板、初始化/接口变更/发布审计/主题目录案例、集中式避坑指南和只读默认的安全修复流程。
- 收紧隐式激活边界：没有文档影响的纯代码修改不会启动完整治理流程；同时移除个人机器路径并改为可移植表达。

## [0.1.0] - 2026-09-14

- Established the initial r-doc Skill source copy.
- Added project-level `AGENTS.md` and documentation-governance conventions under `docs/`.
- Added lifecycle checklists, metadata rules, project-configuration guidance, and core templates.
- Completed the initial verification of the global installation copy.

### 中文摘要

- 建立初始 r-doc Skill 源副本。
- 增加项目级 `AGENTS.md` 和 `docs/` 文档治理约定。
- 增加生命周期检查清单、元数据规则、项目配置指南和核心模板。
- 完成全局安装副本的初始验证。
