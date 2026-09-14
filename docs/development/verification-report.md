---
id: VERIFICATION-RDOC-001
type: report
status: active
title: r-doc 可复现验证记录
created: 2026-09-14
updated: 2026-09-14
---

# r-doc 可复现验证记录

## 摘要

这份记录保存当前源副本的可复现验证结果，避免只在发布说明中口头声称“已验证”。命令均从项目根目录执行，脚本不会修改项目文档。

## 当前结果

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| Skill 包结构、入口、链接和脚本语法 | `python skills/r-doc/scripts/validate_skill.py skills/r-doc` | PASS |
| 安全结构修复预览 | `python skills/r-doc/scripts/repair_docs.py --root .` | PASS，无待写入修复 |
| 项目文档结构、索引、链接、元数据和敏感值 | `python skills/r-doc/scripts/audit_docs.py --root . --strict` | PASS |
| 临时项目行为场景 | `python -m unittest discover -s skills/r-doc/tests -p 'test_*.py'` | PASS，12 tests |
| 官方 Skill creator 校验 | `python quick_validate.py skills/r-doc` | PASS |
| 本地 npx skills 发现 | `npx skills add . --list` | PASS，发现 1 个 r-doc |
| 工作树空白错误 | `git diff --check` | PASS |

## 覆盖的临时项目场景

- 入口和嵌套索引完整时严格审计通过；
- 缺少根 `AGENTS.md` 时报告入口错误；
- 断链时报告目标和行号；
- 未被索引的主题文档时报告覆盖缺口；
- 检测到疑似密钥时报告敏感内容；
- 发现重复文档 ID 时报告冲突。
- 预览不会写入文件；显式应用后可重复运行且不再产生修复；
- 缺失索引链接会被补入；并发修改会被拒绝，避免覆盖新内容。

## 限制

这份记录证明当前源副本和确定性验证路径可复现，不等同于真实外部项目的长期采用数据。发布后应继续补充来自真实项目的匿名化验证记录和兼容性反馈。

返回：[开发文档索引](README.md) · [文档总索引](../README.md)
