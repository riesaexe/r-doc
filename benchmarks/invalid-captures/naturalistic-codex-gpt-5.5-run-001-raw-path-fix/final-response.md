已同步完成：

- 实现改为返回 `display_name`：[handler.py](C:/Users/RiESA/AppData/Local/Temp/rdoc-naturalistic-9rlmmy3r/src/handler.py:2)
- 测试断言同步为 `display_name`：[test_api.py](C:/Users/RiESA/AppData/Local/Temp/rdoc-naturalistic-9rlmmy3r/tests/test_api.py:7)
- API 文档同步为 `display_name`：[api.md](C:/Users/RiESA/AppData/Local/Temp/rdoc-naturalistic-9rlmmy3r/docs/api.md:3)
- 新增 [pytest.ini](C:/Users/RiESA/AppData/Local/Temp/rdoc-naturalistic-9rlmmy3r/pytest.ini:1)，让裸 `pytest` 命令也能稳定导入项目包

验证结果：`pytest -q` 通过，`1 passed`。旧字段 `user_name` 已无残留引用。