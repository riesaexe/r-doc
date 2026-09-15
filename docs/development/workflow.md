---
id: GUIDE-RDOC-DEV-001
type: guide
status: active
title: r-doc 开发与验证流程
created: 2026-09-14
updated: 2026-09-15
related_code:
  - skills/r-doc/SKILL.md
---

# r-doc 开发与验证流程

## 日常修改

1. 从项目根 AGENTS.md 和 docs/README.md 开始加载上下文。
2. 确认修改属于入口、工作流、生命周期、元数据、配置还是模板。
3. 修改 skills/r-doc/ 源文件，不直接修改全局安装副本。
4. 如果改变了用户可见行为，更新本文件或对应设计/发布文档。

## 确定性验证

在项目根目录运行以下命令。脚本只读检查，不会替项目修改文档：

```bash
python -m pip install -r requirements-dev.txt
python skills/r-doc/scripts/validate_skill.py skills/r-doc
python skills/r-doc/scripts/repair_docs.py --root .
python skills/r-doc/scripts/audit_docs.py --root . --strict
python -m unittest discover -s skills/r-doc/tests -p 'test_*.py'
```

`requirements-dev.txt` 提供确定性 frontmatter 解析所需的 PyYAML。`validate_skill.py` 检查 Skill 包的入口、UI 元数据、内部链接、脚本语法、机器特定路径和敏感值。`repair_docs.py` 默认只预览安全结构修复，只有显式 `--apply` 才写入。`audit_docs.py` 使用 PyYAML 解析嵌套 frontmatter，解析错误会作为明确 finding 报告，不会静默丢弃列表；它还检查项目入口、嵌套索引、链接、索引覆盖、frontmatter 和敏感值。`--strict` 会把元数据缺失等警告视为失败。

## 验证顺序

1. 检查 frontmatter、命名和占位符。
2. 检查 SKILL.md 引用的 references 是否存在。
3. 检查引用文档中的 Markdown 相对链接。
4. 运行确定性脚本和单元测试。
5. 用临时项目验证根入口、根索引、嵌套索引、冲突和排除目录。
6. 检查敏感信息和未经脱敏的示例。
7. 验证通过后再同步全局安装副本。

## 同步原则

同步前确认项目源副本和全局副本的版本一致。同步后重新检查全局副本的文件树和入口内容。若同步失败，保留旧安装副本并报告，不留下半更新状态。

## 变更记录

行为变化、触发条件变化、文档状态规则变化和模板结构变化都需要在 CHANGELOG.md 的 Unreleased 或对应版本中记录。

## English workflow

1. Load `AGENTS.md` and `docs/README.md` first.
2. Identify whether the change affects entrypoints, workflow, lifecycle, metadata, configuration, templates, public behavior, or release records.
3. Edit the source under `skills/r-doc/`; do not develop directly in the global installation copy.
4. If user-visible behavior changes, update this workflow or the relevant design/release document. Public project documentation and Release notes should be bilingual; runtime Skill instructions remain English-only to control context cost.

Run the deterministic checks from the repository root:

```bash
python skills/r-doc/scripts/validate_skill.py skills/r-doc
python skills/r-doc/scripts/repair_docs.py --root .
python skills/r-doc/scripts/audit_docs.py --root . --strict
python -m unittest discover -s skills/r-doc/tests -p 'test_*.py'
```

Verify frontmatter and placeholders, referenced resources, Markdown links, helper output, temporary-project scenarios, sensitive-value handling, and the source/global-copy version boundary. Synchronize the validated source only after the checks pass. Record behavior, trigger, status-rule, template, and release changes in `CHANGELOG.md`; each release section carries English notes and a Chinese summary.

Back to: [development index](README.md) · [documentation index](../README.md)
