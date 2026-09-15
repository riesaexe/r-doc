已同步完成：

- [src/repository.py](<fixture-root>\src\repository.py:2) 查询改为 `SELECT display_name FROM users`
- [tests/test_repository.py](<fixture-root>\tests\test_repository.py:4) 测试期望同步为 `display_name`
- [docs/database.md](<fixture-root>\docs\database.md:3) 数据库文档同步为新列名

验证结果：`PYTHONPATH=.` 下运行 `pytest`，`1 passed`。另外已用 `rg` 确认仓库里没有残留 `user_name` 引用。