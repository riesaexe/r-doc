已同步 `user_created` 事件契约为 `display_name`：

- Producer: [src/events.py](<fixture-root>/src/events.py:2)
- Test: [tests/test_events.py](<fixture-root>/tests/test_events.py:7)
- Docs: [docs/events.md](<fixture-root>/docs/events.md:3)

验证结果：`PYTHONPATH=项目根目录 pytest` 通过，`1 passed`。直接跑 `pytest` 时当前临时目录环境没有把 `src` 放进导入路径，会报 `ModuleNotFoundError: No module named 'src'`，但契约行为本身已通过测试。