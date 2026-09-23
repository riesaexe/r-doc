# 实际使用案例

[English version](examples.md)

## 案例 1：初始化已有仓库

假设仓库已经有源代码和面向用户的 README，但没有项目文档入口：

~~~text
storefront/
├── README.md
├── src/
└── tests/
~~~

可以这样请求：

~~~text
$r-doc 检查这个仓库并建立文档入口。先展示安全修复计划，保留已有事实，不要修改业务代码。
~~~

预览结果可能是：

~~~text
r-doc repair: PLAN
CREATE AGENTS.md - 创建缺失的项目入口
CREATE docs/README.md - 创建缺失的文档索引
~~~

用户请求已授权初始化且预览符合范围时，在同一任务使用 `--apply` 应用该计划，不必再请求一次确认；之后在 `AGENTS.md` 中补充项目专属命令和规则。生成的文件只是导航骨架，不代表仓库知识已经完整。

## 案例 2：追踪接口变更

如果 `POST /users` 新增必填的 `role` 字段，可以先请求影响分析：

~~~text
$r-doc 公共 POST /users 请求现在要求 role。追踪文档影响，更新 API 和测试文档，并报告实现、测试与现有文档之间的冲突。
~~~

预期报告应识别受影响的 API 契约、请求示例、校验行为、测试场景、迁移或兼容性说明以及发布文档。如果代码与设计不一致，r-doc 会同时报告两组事实，而不是静默选择其中一组。

## 案例 3：发布前审计

从项目根目录运行确定性检查：

~~~bash
python skills/r-doc/scripts/repair_docs.py --root .
python skills/r-doc/scripts/audit_docs.py --root . --strict
~~~

第一条命令只预览安全的结构性修复。第二条命令检查入口、嵌套索引、链接、覆盖范围、元数据、重复 ID 和常见敏感值模式。结构审计通过不代表产品声明都是真实的；发布报告仍应记录语义复核和未决决策。

## 案例 4：聚焦的主题目录

如果项目有独立的 API 文档，可以用一个索引定义边界：

~~~text
docs/
├── README.md
└── api/
    ├── README.md
    ├── users.md
    └── billing.md
~~~

`docs/api/README.md` 说明 API 文档范围，链接父级索引，列出 `users.md` 和 `billing.md`，并声明推荐阅读顺序。新增 `payments.md` 时，应在同一变更中把它加入该索引；修复器可以补充缺失链接，但不会重写 API 内容。
