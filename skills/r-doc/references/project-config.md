# 项目级配置

## 查找顺序

按以下顺序查找项目配置，命中第一个有效文件后读取；若多个文件都存在，报告重复配置并请求用户选择，不静默合并：

~~~text
.r-doc.yaml
docs/r-doc.yaml
r-doc.yaml
~~~

没有配置时使用默认规则。配置只能覆盖项目约定，不能关闭敏感信息保护、冲突报告、非破坏性修改和完成证据要求。

## 推荐结构

~~~yaml
version: 1
project_type: auto
docs_root: docs
required_document_types:
  - requirements
  - design
  - testing
exclude:
  - .git
  - node_modules
  - dist
  - build
gates:
  review: audit
  release: audit
relationships:
  require_for:
    requirements:
      - design
    design:
      - testing
~~~

可选字段：

- project_type：auto 或项目类型名称；自动识别结果可由此覆盖；
- docs_root：项目文档根目录，默认为 docs；
- required_document_types：当前项目明确要求的文档类型；
- exclude：额外排除目录或文件模式；
- gates：各阶段的 advisory、audit 或 blocking 强度；
- relationships.require_for：文档类型之间的最小关联关系。

未知字段或无效配置应报告并按默认规则继续检查，不要把配置错误当成通过。
