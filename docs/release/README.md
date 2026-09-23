---
id: REL-RDOC-001
type: release
status: active
title: r-doc 发布指南
created: 2026-09-14
updated: 2026-09-23
---

# r-doc 发布指南

## 发布对象

发布对象是 skills/r-doc/ 目录本身，目标是让其他工具能够读取其中的 SKILL.md 和支持资源。`~/.agents/skills/r-doc/` 是本机安装位置，不是发布源。

## 当前版本

- 版本文件：[VERSION](../../VERSION)
- 变更记录：[CHANGELOG.md](../../CHANGELOG.md)
- 当前发布版本：1.0.0（GitHub tag `v1.0.0`）；源提交：`eb920fe493da22a909773867842336498c62af1d`

## 发布步骤

### GitHub Release 执行面

正式 GitHub Release 的创建、说明写入和附件上传必须使用本机 Git Credential Manager 返回的凭据，通过 GitHub REST API 完成。发布脚本先按 tag 查询现有 Release，再按需创建和上传缺失附件，最后用 API 验证 draft=false、tag 和附件名称/大小；重复执行不得创建重复 Release 或重复附件。不得把 PAT、密码或 git credential fill 输出写入日志、命令输出或仓库。浏览器只能用于只读查看公开结果，不能用于创建、编辑或上传 Release。

Git 推送、标签推送和 npx 验证同样从本机命令行完成。使用该发布面需要先取得用户对外部发布的明确授权；没有授权时只做本地验证和打包。

1. 在 skills/r-doc/ 中完成修改。
2. 更新项目文档和 CHANGELOG.md。
3. 预览 `repair_docs.py` 的安全修复，确认没有未经审查的计划；再运行 `validate_skill.py`、`audit_docs.py --strict`、单元测试和官方 Skill 校验器。
4. 更新 VERSION，以及 skills/r-doc/SKILL.md 的 metadata.version。
5. 确认公开 GitHub 仓库结构和许可证。
6. 按 [GitHub 与 npx skills 发布指南](github-and-npx.md) 和 [发布检查清单](release-checklist.md) 执行校验和临时项目 QA。
7. 生成带版本号的发布包（如果目标平台需要），例如 r-doc-v0.4.1.zip；包内顶层目录固定为 r-doc/。
8. 将验证通过的发布内容同步到全局安装目录。
9. 验证全局副本的版本、文件树和入口文件。
10. 发布后记录仓库地址、标签、实际包路径、校验结果和已知限制。

## v1.0.0 发布记录

- 仓库与发布页：[riesaexe/r-doc](https://github.com/riesaexe/r-doc) · [GitHub Release v1.0.0](https://github.com/riesaexe/r-doc/releases/tag/v1.0.0)。签名提交与注释标签本机验证通过；GitHub API 对发布提交返回 `verification.verified=true`。
- 发布包：[r-doc-v1.0.0.zip](https://github.com/riesaexe/r-doc/releases/download/v1.0.0/r-doc-v1.0.0.zip)，121,276 字节，SHA-256：`f10b2ee47ae14c9393e38486f009dfd8bff16468b1c435605df140939f93281e`。包内顶层目录为 `r-doc/`。
- 校验：Skill 校验器、文档严格审计、136 项单元测试、官方 Skill 校验器和公开仓库 npx 发现均通过；公开 npx 全局安装已完成，安装器报告 PromptScript 不支持全局安装。安装副本的 61 个受版本控制文件与发布提交内容逐一匹配（忽略平台换行差异）。
- 评测记录：[naturalistic benchmark 总览](../development/benchmarks.md)记录用户确认的 `gpt-6-luna` 七类任务、每类 10 对、共 140 次运行。124/140 项任务 outcome 通过、forbidden read 为 0/140；但 70 个 treatment 的 visibility 均为 `unknown`，有效配对比较为 0，因此结果仅作描述性证据。
- SkillHub 导入暂缓：当前 [SkillHub registry](https://skillhub.fyi/r/@r-doc/skills/r-doc) 已有 `r-doc` 1.0.2 作为 latest，而 GitHub 本次发布版本为 1.0.0。为避免将较旧版本标为 latest，本次未导入；需先完成两个分发面的版本对齐。

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
- Current release: 1.0.0 (GitHub tag `v1.0.0`); source commit: `eb920fe493da22a909773867842336498c62af1d`.

### Release steps

#### GitHub Release execution surface

Formal GitHub Release creation, release-note writing, and asset upload must use credentials returned by the local Git Credential Manager through the GitHub REST API. The flow must look up the tag first, create the Release only when it is absent, upload only missing assets, and read the Release back through the API to verify draft=false, the tag, and asset name/size. Re-running the flow must not create duplicate Releases or assets. Never write a PAT, password, or git credential fill output to logs, command output, or the repository. The browser is read-only for checking the public result; it is not a release execution surface.

Git pushes, tag pushes, and npx verification also run from the local command line. Obtain explicit user authorization before making the external publication; without it, stop at local validation and packaging.

1. Complete the source change under `skills/r-doc/`.
2. Update project documentation and `CHANGELOG.md`; release notes must contain both English and Chinese summaries.
3. Preview `repair_docs.py`, then run `validate_skill.py`, `audit_docs.py --strict`, the unit tests, and the official Skill validator when available.
4. Update `VERSION` and `metadata.version` in `skills/r-doc/SKILL.md`.
5. Confirm the public GitHub repository structure and license.
6. Follow the [GitHub and npx skills guide](github-and-npx.md) and [release checklist](release-checklist.md), including temporary-project QA.
7. Build a versioned package when the target platform requires one, for example `r-doc-v0.4.1.zip` with a top-level `r-doc/` directory.
8. Synchronize validated source files to the global installation copy.
9. Recheck the global copy's version, file tree, and entrypoint.
10. Record the repository URL, tag, package path, verification results, and known limitations after release.

### v1.0.0 publication record

- Repository and release: [riesaexe/r-doc](https://github.com/riesaexe/r-doc) · [GitHub Release v1.0.0](https://github.com/riesaexe/r-doc/releases/tag/v1.0.0). The signed commit and annotated tag were verified locally; the GitHub API returned `verification.verified=true` for the release commit.
- Package: [r-doc-v1.0.0.zip](https://github.com/riesaexe/r-doc/releases/download/v1.0.0/r-doc-v1.0.0.zip), 121,276 bytes, SHA-256 `f10b2ee47ae14c9393e38486f009dfd8bff16468b1c435605df140939f93281e`; the archive has a top-level `r-doc/` directory.
- Validation: Skill validation, strict documentation audit, 136 unit tests, the official Skill validator, and public-repository npx discovery passed. Public npx global installation completed; the installer reports that PromptScript does not support global installation. All 61 version-controlled installed files match the release commit after normalizing platform line endings.
- Benchmark: [Naturalistic benchmark overview](../development/benchmarks.md) records the user-approved `gpt-6-luna` run: seven task classes, 10 pairs per class, 140 runs. Task outcomes passed 124/140 and forbidden reads were 0/140; all 70 treatment visibility values are `unknown`, leaving zero valid paired comparisons, so the result is descriptive evidence only.
- SkillHub import is pending: the current [SkillHub registry](https://skillhub.fyi/r/@r-doc/skills/r-doc) already has `r-doc` 1.0.2 as `latest`, while this GitHub release is 1.0.0. To avoid marking an older version as latest, this release was not imported; align versions across the two distribution surfaces first.

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
