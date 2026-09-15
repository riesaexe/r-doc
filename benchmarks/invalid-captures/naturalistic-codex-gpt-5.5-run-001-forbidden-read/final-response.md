已同步完成：实现、API 文档、测试现在都使用 `display_name`。

改动文件：
- [src/handler.py](C:/Users/RiESA/AppData/Local/Temp/rdoc-naturalistic-2uyu1swk/src/handler.py:2)
- [tests/test_api.py](C:/Users/RiESA/AppData/Local/Temp/rdoc-naturalistic-2uyu1swk/tests/test_api.py:7)
- [docs/api.md](C:/Users/RiESA/AppData/Local/Temp/rdoc-naturalistic-2uyu1swk/docs/api.md:3)

验证结果：`python -m pytest` 通过，`1 passed`。另外已搜索确认项目里不再有 `user_name` 引用。裸 `pytest` 在这个环境里有 import path 问题，但 `python -m pytest` 正常。