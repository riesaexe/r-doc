---
id: REL-RDOC-001
type: release
status: active
title: r-doc 发布指南
created: 2026-09-14
updated: 2026-09-15
---

# r-doc 发布指南

## 发布对象

发布对象是 skills/r-doc/ 目录本身，目标是让其他工具能够读取其中的 SKILL.md 和支持资源。`~/.agents/skills/r-doc/` 是本机安装位置，不是发布源。

## 当前版本

- 版本文件：[VERSION](../../VERSION)
- 变更记录：[CHANGELOG.md](../../CHANGELOG.md)
- 当前发布版本：0.2.17；源代码版本：0.2.17（下一次行为变更按 PATCH 递增）

## 发布步骤

1. 在 skills/r-doc/ 中完成修改。
2. 更新项目文档和 CHANGELOG.md。
3. 预览 `repair_docs.py` 的安全修复，确认没有未经审查的计划；再运行 `validate_skill.py`、`audit_docs.py --strict`、单元测试和官方 Skill 校验器。
4. 更新 VERSION，以及 skills/r-doc/SKILL.md 的 metadata.version。
5. 确认公开 GitHub 仓库结构和许可证。
6. 按 [GitHub 与 npx skills 发布指南](github-and-npx.md) 和 [发布检查清单](release-checklist.md) 执行校验和临时项目 QA。
7. 生成带版本号的发布包（如果目标平台需要），例如 r-doc-v0.2.17.zip；包内顶层目录固定为 r-doc/。
8. 将验证通过的发布内容同步到全局安装目录。
9. 验证全局副本的版本、文件树和入口文件。
10. 发布后记录仓库地址、标签、实际包路径、校验结果和已知限制。

## 版本规则

- PATCH：文案修正、链接修正、非行为性模板修正；
- MINOR：新增文档治理能力、模板或兼容场景，保持既有行为；
- MAJOR：改变默认工作流、门槛、状态语义或破坏既有配置。

未完成发布验证前，版本保持在 Unreleased，不把未经验证的副本称为正式发布。

## 升级策略

0.2.x 的补丁版本也可能收紧确定性审计覆盖，因此采用者应将精确标签固定在 CI 中，并在升级前执行预览和严格审计。完整的逐版本行为变化、风险和迁移动作见 [版本迁移总览](../../skills/r-doc/references/migration-matrix.md)。

## SkillHub 流程

SkillHub 不作为源文件仓库。GitHub 仓库公开并验证可通过 npx skills 安装后，再将 GitHub 仓库地址手动导入 SkillHub；平台导入结果单独检查，不反向修改项目源文件。

## 当前限制

发布包格式和自动同步脚本尚未绑定到某个外部工具或仓库平台。确认目标平台后，再增加对应的打包、校验和发布自动化，避免提前引入不可移植的流程。

## 返回

[文档总索引](../README.md)

## English release guide

### What is released

The release unit is the `skills/r-doc/` directory, so other tools can read `SKILL.md` and its support resources. `~/.agents/skills/r-doc/` is a local installation copy, not the source of truth.

### Current version

- Version file: [VERSION](../../VERSION)
- Changelog: [CHANGELOG.md](../../CHANGELOG.md)
- Current release: 0.2.17; source version: 0.2.17.

### Release steps

1. Complete the source change under `skills/r-doc/`.
2. Update project documentation and `CHANGELOG.md`; release notes must contain both English and Chinese summaries.
3. Preview `repair_docs.py`, then run `validate_skill.py`, `audit_docs.py --strict`, the unit tests, and the official Skill validator when available.
4. Update `VERSION` and `metadata.version` in `skills/r-doc/SKILL.md`.
5. Confirm the public GitHub repository structure and license.
6. Follow the [GitHub and npx skills guide](github-and-npx.md) and [release checklist](release-checklist.md), including temporary-project QA.
7. Build a versioned package when the target platform requires one, for example `r-doc-v0.2.17.zip` with a top-level `r-doc/` directory.
8. Synchronize validated source files to the global installation copy.
9. Recheck the global copy's version, file tree, and entrypoint.
10. Record the repository URL, tag, package path, verification results, and known limitations after release.

### Version policy

- PATCH: wording, link, or non-behavioral template fixes;
- MINOR: new documentation-governance capabilities, templates, or compatible scenarios;
- MAJOR: changes to the default workflow, gates, status semantics, or incompatible configuration.

Keep a change under `Unreleased` until release verification is complete. Never describe an unverified copy as an official release.

### Upgrade and SkillHub notes

Patch releases in 0.2.x may tighten deterministic audit coverage. Pin exact tags in CI and run preview plus strict audit before upgrading. SkillHub is a distribution surface, not the source repository: publish and verify GitHub/npx first, then import the public repository URL manually.

### Current limitation

The package format and automatic synchronization script are not coupled to an external platform. Add platform-specific packaging only after the target is confirmed.

Back to: [documentation index](../README.md)
