# 文档元数据

## 推荐 frontmatter

主题文档优先使用 YAML frontmatter：

~~~yaml
---
id: DOC-001
type: design
status: draft
title: 示例技术设计
created: 2026-09-14
updated: 2026-09-14
owner: team-name
review_after: 2026-10-01
related_code:
  - src/example.ts
related_docs:
  - DOC-002
supersedes: DOC-000
---
~~~

必需字段：

- id：项目内稳定、唯一的文档标识；
- type：文档类型，例如 requirements、design、adr、api、testing、release；
- status：见状态流转；
- title：与正文标题一致；
- created、updated：使用 ISO 8601 日期或带时区的时间。

条件字段：

- owner：需要持续维护或审查的文档；
- review_after：有复审周期的文档；
- related_code：受代码、配置或数据模型影响的文档，使用相对路径；
- related_docs：依赖其他文档事实的文档；
- supersedes：替代旧文档时使用。

根 AGENTS.md 和索引 README.md 是导航入口，允许不使用完整 frontmatter，但必须有清晰标题、范围、更新时间或等价信息，并满足导航要求。

## 状态语义

~~~text
draft      仍在编写，不能作为最终规范
proposed   已形成方案，等待审查或批准
active     当前有效的项目事实或规范
superseded 已被新文档替代，必须指向替代文档
archived   历史资料，默认不参与当前规范判断
~~~

不要用 active 掩盖未确认的草稿，也不要把已实现但与期望不一致的代码自动写成 active 规范。

## 文档类型

类型不是固定枚举；至少保持以下常用类型语义稳定：

~~~text
requirements  目标、范围、验收标准
design        技术方案和边界
adr           架构或重大决策
api           接口、命令、数据格式和兼容性
testing       测试策略、计划、报告和验证证据
release       发布、变更和升级说明
operations    部署、运维、迁移、回滚和排障
guide         面向维护者或用户的操作说明
policy        项目规则和约束
~~~
