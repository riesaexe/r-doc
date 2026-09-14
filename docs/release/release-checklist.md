# r-doc 发布检查清单

## 源文件

- [ ] skills/r-doc/SKILL.md 的 name、description 和 metadata.version 正确
- [ ] agents/openai.yaml 可读取，隐式调用策略符合预期
- [ ] assets/r-doc.svg 存在且能在 README 中渲染
- [ ] references/ 中没有未完成占位符
- [ ] 所有入口引用的文件都存在
- [ ] 模板没有真实密钥或敏感示例
- [ ] 根 README 的 GitHub 和 npx skills 安装命令已更新为实际仓库地址
- [ ] LICENSE 已选择并提交

## 行为验证

- [ ] 能识别项目根目录和既有 AGENTS.md/docs/
- [ ] 能建立或修复 AGENTS.md、docs/README.md 和嵌套 README.md
- [ ] 能检查缺失、过时、重复、冲突和断链
- [ ] 能区分源副本与全局安装副本
- [ ] 能在高风险或事实冲突时暂停并报告

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
- [ ] npx skills add <owner>/<repo> --list 能发现 r-doc
- [ ] npx skills add <owner>/<repo> --skill r-doc -g -y 安装成功
- [ ] SkillHub 已从 GitHub 地址手动导入并完成页面检查
