已同步完成：实现、API 文档和测试都从 `user_name` 改为 `display_name`。

验证结果：`python -m pytest` 通过，`1 passed`。我也重新搜索了字段引用，项目里只剩 `display_name`，没有残留的 `user_name`。