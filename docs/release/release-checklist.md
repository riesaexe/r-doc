---
id: REL-CHECKLIST-001
type: checklist
status: active
title: r-doc 发布检查清单
created: 2026-09-14
updated: 2026-09-14
---

# r-doc 发布检查清单

## 源文件

- [ ] skills/r-doc/SKILL.md 的 name、description 和 metadata.version 正确
- [ ] agents/openai.yaml 可读取，隐式调用策略符合预期
- [ ] assets/r-doc.svg 存在且能在 README 中渲染
- [ ] references/ 中没有未完成占位符
- [ ] 所有入口引用的文件都存在
- [ ] 模板没有真实密钥或敏感示例
- [ ] references/、scripts/ 和 tests/ 的中英文入口与目录结构一致
- [ ] `validate_skill.py`、`audit_docs.py --strict` 和单元测试通过
- [ ] Agent 行为评测证据通过 `evaluate_agent.py --strict --json` 校验，且证据不含敏感值
- [ ] `repair_docs.py` 的默认预览没有未经确认的待写入修复
- [ ] 根 README 的 GitHub 和 npx skills 安装命令已更新为实际仓库地址
- [ ] LICENSE 已选择并提交

## 行为验证

- [ ] 能识别项目根目录和既有 AGENTS.md/docs/
- [ ] 能建立或修复 AGENTS.md、docs/README.md 和嵌套 README.md
- [ ] 能检查缺失、过时、重复、冲突和断链
- [ ] 能区分源副本与全局安装副本
- [ ] 能在高风险或事实冲突时暂停并报告
- [ ] 具备至少一个真实或临时项目验证记录

## 版本与记录

- [ ] VERSION 与 SKILL.md 的 metadata.version 一致
- [ ] CHANGELOG.md 已记录本次变更
- [ ] 发布说明包含兼容性和已知限制
- [ ] 发布包只包含运行所需的 r-doc 文件

## 安装副本

- [ ] 全局副本来自验证通过的项目源副本
- [ ] 全局副本文件树与发布包一致
- [ ] 全局副本入口和版本已复核
- [ ] 失败时保留旧版本，不留下半更新状态

## 平台验证

- [ ] GitHub 仓库为公开仓库且包含 skills/r-doc/SKILL.md
- [ ] npx skills add riesaexe/r-doc --list 能发现 r-doc
- [ ] npx skills add riesaexe/r-doc --skill r-doc -g -y 安装成功
- [ ] SkillHub 已从 GitHub 地址手动导入并完成页面检查
