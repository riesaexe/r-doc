---
name: r-doc
description: "Project documentation governance: automatically initialize, index, audit, and maintain AGENTS.md, docs/, and planning, requirements, design, API, testing, release, and deployment documents. Use when users ask to manage project documentation, check documentation consistency, update AGENTS.md, or trace change impact; not a replacement for business-code implementation."
metadata:
  version: "0.1.0"
---

# r-doc：项目文档治理

## 目标

把项目文档维护成一个可导航、可审查、低上下文成本的知识库：维护者或 AI 先读项目根目录的 `AGENTS.md`，再按索引只加载完成当前任务所需的最小文档集合。

这是项目级文档规范，不是业务代码实现规范。项目文档体系中的“最高优先级”不覆盖系统指令、用户当前要求或工具更高层级的规则。

## 何时使用

在以下情况自动使用，或用户显式调用 `$r-doc` 时使用：

- 初始化项目、整理项目知识或补齐文档入口；
- 处理计划、需求、设计、架构决策、接口、测试、发布、部署、规则或流程文档；
- 代码、配置、接口、数据模型、流程、部署或架构发生变化；
- 代码审查、合并前、发布前或维护阶段需要确认文档是否同步；
- 用户要求检查文档缺失、过时、重复、冲突、断链或上下文加载顺序。

纯粹的局部代码重构，且不影响对外行为、数据、配置、架构或项目规则时，不要无谓启动完整文档治理流程。

## 不可违反的约束

1. 以项目根目录为作用域。优先使用 Git 根目录；非 Git 项目使用用户明确的项目根目录。
2. 项目根目录必须有 `AGENTS.md`，并建立 `docs/README.md`。复杂主题目录也使用固定名称 `README.md` 作为索引。
3. `AGENTS.md` 只放项目概览、范围、快速开始、上下文加载顺序、关键目录、命令、强制规则、禁止事项、路线指引和 `docs/` 索引。详细知识必须链接到 `docs/`。
4. 每篇主题文档只聚焦一个主题；主题混杂、难以定位或过长时拆分。不要为了凑目录创建空文档。
5. 文档必须主动同步代码、配置、接口、流程、部署和决策变更；关键约束、踩坑和非显而易见决策必须落档。
6. 不写入密钥、令牌、密码、个人敏感信息或可用于绕过安全控制的真实值。发现疑似敏感信息时停止写入并报告。
7. 已有 `AGENTS.md`、`docs/` 或文档内容时采用非破坏性合并：保留事实和历史，不直接覆盖或删除；发现冲突先报告并提出唯一事实来源建议。
8. 默认只修改文档、索引、模板、元数据和文档注释，不修改业务代码。读取代码和 Git diff 只用于判断文档影响。
9. 不把“文件存在”当作“文档完成”。必须检查索引、链接、状态、关联关系和受影响内容的一致性。

## 标准流程

根据任务规模选择轻量或完整流程，但高影响任务必须完成全部相关检查：

1. 识别当前开发阶段、任务范围和可能受影响的文档类型。
2. 读取项目根 `AGENTS.md`（如存在）、`docs/README.md`、相关子目录 `README.md`、项目级 `.r-doc.yaml` 配置，以及当前任务直接关联的文档。
3. 检查项目结构、Git 状态/差异和相关代码；只读取判断文档影响所需的代码。
4. 建立文档清单，标出缺失、过时、未索引、断链、状态失效、重复、冲突和疑似敏感信息。
5. 先提出必要的澄清问题，再给出集中式修改计划；在计划获用户确认前，不执行文档写入、移动、归档或配置变更。
6. 按计划创建或更新 `AGENTS.md`、索引、主题文档、元数据和项目配置。机械性的索引、链接和日期更新可在确认后自动完成。
7. 验证上下文加载顺序、索引覆盖、链接、元数据、关联关系、阶段门槛和敏感信息。
8. 输出治理报告：范围、发现的问题、已完成修改、阻塞项、非阻塞项、验证证据和当前阶段是否满足门槛。

详细阶段清单见 [references/lifecycle-checklists.md](references/lifecycle-checklists.md)，完整操作流程见 [references/workflow.md](references/workflow.md)。

## 文档结构与索引

默认结构如下；优先保留项目已有合理结构，只在缺失时补齐：

```text
AGENTS.md
docs/
└── README.md
```

需要时再建立 `requirements/`、`design/`、`decisions/`、`api/`、`testing/`、`releases/`、`operations/` 等主题目录。每个主题目录的 `README.md` 必须说明目录范围、文档列表、推荐阅读顺序，并链接父索引和具体文档。根 `AGENTS.md` 必须链接 `docs/README.md`。

推荐的上下文加载顺序是：

```text
AGENTS.md
→ docs/README.md
→ 相关主题目录 README.md
→ 目标文档
→ 目标文档明确链接的补充文档
```

## 状态、关联和冲突

主题文档默认使用以下状态流转：

```text
draft → proposed → active → superseded → archived
```

发现文档与代码、测试或其他文档不一致时，分别说明“期望行为”“当前行为”“冲突位置”和“待确认决策”，不要把现有实现自动改写为规范，也不要用最新文件覆盖其他事实。

元数据规则见 [references/metadata-schema.md](references/metadata-schema.md)。项目覆盖规则见 [references/project-config.md](references/project-config.md)。

## 输出最低标准

最终报告至少包含：

```text
当前阶段与检查范围
发现的问题（缺失、过时、冲突、断链、敏感信息）
已完成的文档更新
仍待处理的阻塞项和非阻塞项
验证方式与结果
当前阶段文档门槛：满足 / 不满足
```

模板只在能减少重复劳动时使用；先读取 [references/templates/README.md](references/templates/README.md)，再按项目类型和当前任务选择模板，不要批量生成无内容的文件。
