已同步完成：

- 事件生产者现在输出 `payload.display_name`
- 事件文档已改为 `display_name`
- 测试断言已更新为新字段名
- 已确认仓库内没有残留 `user_name`

验证：`PYTHONPATH=当前目录 pytest -q` 通过，`1 passed`。