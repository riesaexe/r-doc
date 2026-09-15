已同步完成：

- `src/cli.py` 现在只接受 `--display-name`
- `docs/cli.md` 文档示例已更新为 `--display-name <name>`
- `tests/test_cli.py` 已改为断言 `.display_name`，并新增旧的 `--user-name` 会被拒绝的测试

验证已通过：

```powershell
$env:PYTHONPATH=(Get-Location).Path; pytest
# 2 passed
```