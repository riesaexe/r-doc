---
name: r-doc-zh-cn-reference
description: "面向人类维护者的 r-doc 中文参考指针；运行时加载入口始终是 SKILL.md。"
metadata:
  version: "0.2.13"
  runtime: "human-reference-only"
---

# r-doc 中文参考入口

`SKILL.md` 是唯一的运行时技能入口，也是唯一需要与安装器同步的指令源。这个文件不再复制一套规则，避免中英文入口长期漂移。

面向用户的中文介绍、安装方式和使用示例请阅读项目根目录的 [`README.zh-CN.md`](../../README.zh-CN.md)。

运行时规则仍以 [`SKILL.md`](./SKILL.md) 为唯一指令源；中文公开参考资料请按需阅读[安全修复指南](references/repair.zh-CN.md)、[实际案例](references/examples.zh-CN.md)和[常见避坑指南](references/pitfalls.zh-CN.md)。需要精确的运行时字段、配置和验证契约时，再从英文 canonical references 加载对应技术文档。
