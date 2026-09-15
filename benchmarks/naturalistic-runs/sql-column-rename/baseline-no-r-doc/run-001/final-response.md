已同步完成：

- [src/repository.py](<fixture-root>/src/repository.py:2) 查询改为 `SELECT display_name FROM users`
- [tests/test_repository.py](<fixture-root>/tests/test_repository.py:4) 断言更新为新列名
- [docs/database.md](<fixture-root>/docs/database.md:3) 文档更新为 `display_name`

验证结果：`user_name` 已从 `src`、`tests`、`docs` 中清除；用 `$env:PYTHONPATH=(Get-Location).Path; pytest -q` 跑测试通过，`1 passed`。普通 `pytest -q` 在这个临时目录里会因未配置 `src` 导入路径而失败。