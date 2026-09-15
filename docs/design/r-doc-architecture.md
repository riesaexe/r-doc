---
id: DES-RDOC-001
type: design
status: active
title: r-doc 架构说明
created: 2026-09-14
updated: 2026-09-15
---

# r-doc 架构说明

## 摘要

r-doc 由项目源副本和全局安装副本组成。项目源副本用于版本控制、迭代、审查和发布；全局副本用于本机运行和工具发现。

## 目录关系

~~~text
<project-root>/skills/r-doc/
    ↓ 验证后同步
~/.agents/skills/r-doc/
~~~

源副本包含 SKILL.md、agents/openai.yaml 和 references/。项目文档位于根 docs/，不复制进 Skill 包，避免把开发记录和运行时指令混在一起。

## 不变量

- 源副本是唯一事实来源；
- 全局副本只能由经过验证的源副本同步得到；
- 任何行为变化都必须能追溯到源文件和 CHANGELOG.md；
- Skill 包保持跨工具可读的 Markdown，Codex 专用元数据只放在 agents/openai.yaml；
- 运行时 Skill 不应要求读取本项目的开发文档才能完成普通文档治理任务。

## 资源组织

- SKILL.md：触发边界、硬约束、主流程和引用路由；
- references/workflow.md：初始化、影响分析、冲突和完成检查；
- references/lifecycle-checklists.md：开发阶段门槛；
- references/metadata-schema.md：文档状态和 frontmatter；
- references/project-config.md：项目覆盖配置；
- references/templates/：按需使用的文档模板；
- scripts/：不修改项目文件的确定性验证脚本；
- tests/：验证脚本和临时项目行为测试。
- assets/r-doc.svg：Skill 界面和项目 README 使用的品牌图标。

## 兼容性边界

其他工具是否自动发现 ~/.agents/skills/ 取决于工具自身协议。r-doc 的核心内容保持为普通 Markdown；需要特定工具适配时，应在源项目中增加明确的适配文件，并在发布说明中记录。

## English architecture summary

r-doc has two copies: the version-controlled project source and the local global installation. The source under `<project-root>/skills/r-doc/` is the only source of truth; after validation it is synchronized to `~/.agents/skills/r-doc/` for local discovery and execution.

The source package contains `SKILL.md`, `agents/openai.yaml`, references, deterministic scripts, tests, and the brand asset. Project design, development, benchmark, and release records stay under the root `docs/` and `benchmarks/` directories instead of being loaded as runtime Skill instructions.

The invariants are: only validated source may update the global copy; behavior changes must be traceable to source and `CHANGELOG.md`; the runtime Skill remains portable Markdown; tool-specific metadata stays in `agents/openai.yaml`; and ordinary governance tasks must not depend on reading this repository's development history.

Back to: [design index](README.md) · [documentation index](../README.md)
