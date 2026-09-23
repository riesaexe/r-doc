---
id: GUIDE-RDOC-DEV-001
type: guide
status: active
title: r-doc 开发与验证流程
created: 2026-09-14
updated: 2026-09-23
related_code:
  - skills/r-doc/SKILL.md
---

# r-doc 开发与验证流程

## 日常修改

1. 读取项目级 .r-doc.yaml 并确定治理级别；先读根 AGENTS.md，在 standard/strict 级别继续读 docs/README.md 和相关主题索引。
2. 确认修改属于入口、工作流、生命周期、元数据、配置还是模板。
3. 修改 skills/r-doc/ 源文件，不直接修改全局安装副本。
4. 如果改变了用户可见行为，更新本文件或对应设计/发布文档。
5. 如果改变了重要决策边界，先检索现有决策笔记；必要时更新原笔记或创建带 `supersedes` 的新笔记。

## 确定性验证

在项目根目录运行以下命令。脚本只读检查，不会替项目修改文档：

```bash
python -m pip install -r requirements-dev.txt
python skills/r-doc/scripts/validate_skill.py skills/r-doc
python skills/r-doc/scripts/repair_docs.py --root .
python skills/r-doc/scripts/audit_docs.py --root . --strict
python -m unittest discover -s skills/r-doc/tests -p 'test_*.py'
```

`requirements-dev.txt` 提供确定性 frontmatter 解析所需的 PyYAML。`validate_skill.py` 检查 Skill 包的入口、UI 元数据、内部链接、脚本语法、机器特定路径和敏感值。`repair_docs.py` 默认只预览安全结构修复；当用户请求已授权且预览仅包含安全机械变更时，可在同一任务显式运行 `--apply`，不再额外等待确认。`audit_docs.py` 按 `governance_level` 选择入口、索引和元数据门槛，同时在所有级别检查链接、目标和敏感值。`strict` 级别及 `--strict` 会把警告视为失败。
`audit_docs.py` 还会在存在 `.agents/notes/` 或配置了 `decision_notes.root` 时校验决策笔记的生命周期路径、状态、必需章节、关系、链接和敏感值；该层不要求加入 `docs/` 索引。
生命周期移动先运行 `python skills/r-doc/scripts/decision_notes.py archive <note-path>` 预览；若用户请求已覆盖归档操作且预览符合范围，可在同一任务追加 `--apply`。只在归档目标或影响有实质歧义时暂停询问。

## 验证顺序

1. 检查 frontmatter、命名和占位符。
2. 检查 SKILL.md 引用的 references 是否存在。
3. 检查引用文档中的 Markdown 相对链接。
4. 运行确定性脚本和单元测试。
5. 用临时项目验证所选级别的入口/索引门槛、冲突和排除目录。
6. 检查敏感信息和未经脱敏的示例。
7. 验证通过后再同步全局安装副本。
8. 若归档或 supersede 行为发生变化，补跑生命周期专项测试并核对源/全局副本哈希。

## 同步原则

同步前确认项目源副本和全局副本的版本一致。同步后重新检查全局副本的文件树和入口内容。若同步失败，保留旧安装副本并报告，不留下半更新状态。

## 变更记录

行为变化、触发条件变化、文档状态规则变化和模板结构变化都需要在 CHANGELOG.md 的 Unreleased 或对应版本中记录。

## English workflow

1. Read `.r-doc.yaml` to select the governance level; start with `AGENTS.md`, then load `docs/README.md` and relevant nested indexes at the standard or strict level.
2. Identify whether the change affects entrypoints, workflow, lifecycle, metadata, configuration, templates, public behavior, or release records.
3. Edit the source under `skills/r-doc/`; do not develop directly in the global installation copy.
4. If user-visible behavior changes, update this workflow or the relevant design/release document. Public project documentation and Release notes should be bilingual; runtime Skill instructions remain English-only to control context cost.
5. If an important decision boundary changes, search existing decision notes first; update the owning note or create a linked successor with `supersedes` when the decision changes.

Run the deterministic checks from the repository root:

```bash
python skills/r-doc/scripts/validate_skill.py skills/r-doc
python skills/r-doc/scripts/repair_docs.py --root .
python skills/r-doc/scripts/audit_docs.py --root . --strict
python -m unittest discover -s skills/r-doc/tests -p 'test_*.py'
```

Verify frontmatter and placeholders, referenced resources, Markdown links, helper output, temporary-project scenarios, sensitive-value handling, and the source/global-copy version boundary. Synchronize the validated source only after the checks pass. Record behavior, trigger, status-rule, template, and release changes in `CHANGELOG.md`; each release section carries English notes and a Chinese summary.
`audit_docs.py` also validates decision-note routing and required sections when the optional layer exists. Decision notes remain separate from ordinary `docs/` index coverage but share its link and sensitive-content gates.
The archive helper previews by default and requires `--apply` for a move. When the user's request already authorizes the archive and the preview matches its scope, apply it in the same task; pause only for a material ambiguity. The audit checks supersession targets, links, cycles, and archive dates.

Back to: [development index](README.md) · [documentation index](../README.md)
