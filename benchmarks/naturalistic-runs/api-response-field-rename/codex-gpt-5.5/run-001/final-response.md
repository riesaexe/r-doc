已同步完成：实现、API 文档和测试都统一为 `display_name`。

改动包括：
- [src/handler.py](<fixture-root>/src/handler.py:2) 返回 `{"display_name": ...}`
- [docs/api.md](<fixture-root>/docs/api.md:3) 文档字段更新
- [tests/test_api.py](<fixture-root>/tests/test_api.py:7) 测试期望更新
- 新增 [pytest.ini](<fixture-root>/pytest.ini:1)，让 `pytest` 能稳定导入本地 `src`

验证结果：`pytest` 通过，`1 passed`；`rg "user_name|display_name"` 确认旧字段 `user_name` 已无残留。