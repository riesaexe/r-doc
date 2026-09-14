---
id: GUIDE-RDOC-DEV-001
type: guide
status: active
title: r-doc 开发与验证流程
created: 2026-09-14
updated: 2026-09-14
related_code:
  - skills/r-doc/SKILL.md
---

# r-doc 开发与验证流程

## 日常修改

1. 从项目根 AGENTS.md 和 docs/README.md 开始加载上下文。
2. 确认修改属于入口、工作流、生命周期、元数据、配置还是模板。
3. 修改 skills/r-doc/ 源文件，不直接修改全局安装副本。
4. 如果改变了用户可见行为，更新本文件或对应设计/发布文档。

## 验证顺序

1. 检查 frontmatter、命名和占位符。
2. 检查 SKILL.md 引用的 references 是否存在。
3. 检查引用文档中的 Markdown 相对链接。
4. 用临时项目验证根入口、根索引、嵌套索引、冲突和排除目录。
5. 检查敏感信息和未经脱敏的示例。
6. 验证通过后再同步全局安装副本。

## 同步原则

同步前确认项目源副本和全局副本的版本一致。同步后重新检查全局副本的文件树和入口内容。若同步失败，保留旧安装副本并报告，不留下半更新状态。

## 变更记录

行为变化、触发条件变化、文档状态规则变化和模板结构变化都需要在 CHANGELOG.md 的 Unreleased 或对应版本中记录。
