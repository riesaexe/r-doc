已同步完成：

- [src/cli.py](<fixture-root>/src/cli.py:5) 现在只注册 `--display-name`
- [docs/cli.md](<fixture-root>/docs/cli.md:3) 已更新为新参数
- [tests/test_cli.py](<fixture-root>/tests/test_cli.py:4) 测试新拼写，并验证旧的 `--user-name` 会被拒绝

验证：`python -m pytest -q` 通过，`2 passed`。

补充：这个目录不是 Git 仓库，所以没法用 `git diff/status` 展示变更。裸 `pytest -q` 在当前环境里有导入路径问题，但 `python -m pytest -q` 正常通过。