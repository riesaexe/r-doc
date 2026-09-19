---
id: REL-CHECKLIST-001
type: checklist
status: active
title: r-doc 发布检查清单
created: 2026-09-14
updated: 2026-09-19
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

- [ ] GitHub Release 通过本机 Git Credential Manager + REST API 创建或复用，未使用网页发布流程
- [ ] 已按 tag 做幂等查询，API 回读确认 draft=false、标签、附件名称和大小；重复执行不会重复创建
- [ ] 终端、日志、提交和报告中没有 PAT、密码或 git credential fill 完整输出

- [ ] GitHub 仓库为公开仓库且包含 skills/r-doc/SKILL.md
- [ ] npx skills add riesaexe/r-doc --list 能发现 r-doc
- [ ] npx skills add riesaexe/r-doc --skill r-doc -g -y 安装成功
- [ ] SkillHub 已从 GitHub 地址手动导入并完成页面检查

## 仓库治理

- [ ] `main` 启用分支保护，要求通过 pull request 合并，并禁止 force-push 和删除
- [ ] 发布提交在 GitHub 显示为 Verified；本机必须配置并在 GitHub 账户登记 signing key
- [ ] 如果历史发布提交未签名，不重写已公开的提交和标签；从下一次发布开始执行签名门禁

## English checklist

### Source and behavior

- [ ] `skills/r-doc/SKILL.md` metadata and entrypoint are correct
- [ ] `agents/openai.yaml`, assets, references, scripts, and tests are present
- [ ] Runtime Skill files remain English-only to control context cost; public project docs and release notes are bilingual
- [ ] `validate_skill.py`, `audit_docs.py --strict`, unit tests, and Agent-evidence checks pass
- [ ] The repair preview has no unreviewed writes
- [ ] The README installation commands point to the actual repository
- [ ] No secrets, tokens, passwords, or personal sensitive values are in the diff

### Release record

- [ ] `VERSION` matches `SKILL.md` metadata
- [ ] `CHANGELOG.md` contains English entries and Chinese summaries for the current and every historical release
- [ ] Release notes include compatibility, verification status, and known limitations
- [ ] The package contains only required r-doc files
- [ ] The validated source was synchronized to the global installation copy

### Platform and repository governance

- [ ] The GitHub Release was created or reused through the local Git Credential Manager and REST API, not the web UI
- [ ] The tag lookup and API read-back verified idempotency, draft=false, the tag, and asset name/size
- [ ] No PAT, password, or complete git credential fill output appears in terminals, logs, commits, or reports

- [ ] The public GitHub repository contains `skills/r-doc/SKILL.md`
- [ ] `npx skills add riesaexe/r-doc --list` discovers r-doc
- [ ] `npx skills add riesaexe/r-doc --skill r-doc -g -y` succeeds
- [ ] SkillHub import was checked after GitHub and npx verification
- [ ] `main` has pull-request protection, at least one approval, stale-review dismissal, and no force-push/deletion
- [ ] The release commit is shown as `Verified` on GitHub
- [ ] Existing unsigned release history was not rewritten; signing is a gate for the next release
