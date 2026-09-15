已完成 baseline-no-r-doc 基准捕获。

写出了两个要求的文件：

- [benchmark-trace.jsonl](C:/Users/RiESA/AppData/Local/Temp/rdoc-codex-benchmark-0hgn7qn2/benchmark-trace.jsonl)
- [benchmark-evidence.json](C:/Users/RiESA/AppData/Local/Temp/rdoc-codex-benchmark-0hgn7qn2/benchmark-evidence.json)

处理结果：

- 8 个场景均按固定顺序记录。
- `trace_start` 使用了要求的 `skill_version` 字段。
- trace 共 `151` 条事件，sequence 从 `0` 到 `150` 连续。
- evidence 顶层 key 校验为：`schema_version`, `skill_version`, `agent`, `condition`, `scenarios`。
- `scenarios` 数量为 `8`。
- baseline 条件下所有 `skill_selected` 都是 `"none"`。
- 第 3 个 code-only 场景记录为 `activation: "declined"`；其他 7 个治理场景记录为 `activation: "activated"`。
- 未读取 r-doc skill。
- 敏感场景未打开或读取 `secrets.md` / `.env`。

最终审计中，需要 audit 的场景均已通过；结构修复场景也按要求运行了 `repair_docs.py` 后再运行 `audit_docs.py`。