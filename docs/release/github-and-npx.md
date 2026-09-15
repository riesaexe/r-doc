---
id: REL-GITHUB-NPX-001
type: guide
status: active
title: GitHub 与 npx skills 发布指南
created: 2026-09-14
updated: 2026-09-15
---

# GitHub 与 npx skills 发布指南

## 目标结构

Vercel Labs 的 skills CLI 通过 GitHub 或其他 Git 源安装 Skill。公开仓库应保留以下路径：

```text
<repository-root>/
├── skills/
│   └── r-doc/
│       ├── SKILL.md
│       ├── agents/
│       ├── references/
│       ├── scripts/
│       ├── tests/
│       └── assets/
├── README.md
├── LICENSE
└── CHANGELOG.md
```

SKILL.md 的 frontmatter 至少包含 name 和 description。r-doc 的源目录还包含可复现的验证脚本和测试，发布时应一并保留。r-doc 的源目录已经符合 skills/r-doc/SKILL.md 约定。

## 本地发现检查

在仓库根目录运行：

```bash
python -m pip install -r requirements-dev.txt
npx skills add . --list
python skills/r-doc/scripts/validate_skill.py skills/r-doc
python skills/r-doc/scripts/repair_docs.py --root .
python skills/r-doc/scripts/audit_docs.py --root . --strict
python -m unittest discover -s skills/r-doc/tests -p 'test_*.py'
```

输出中应能看到 r-doc。这个命令只用于列出发现结果，不代表已经完成公开发布。

## GitHub 发布

公开发布前需要确定 GitHub owner/repository、默认分支和许可证。准备完成后：

1. 在本地初始化或连接 Git 仓库；
2. 提交 skills/r-doc、README、docs、VERSION、CHANGELOG 和 LICENSE；
3. 推送默认分支到公开 GitHub 仓库；
4. 创建与 VERSION 一致的版本标签，例如 v0.2.12；
5. 创建 GitHub Release，附上变更说明和必要的发布包；
6. 从公开仓库地址执行 npx 安装验证。

## npx skills 安装验证

本项目使用 `riesaexe/r-doc` 作为 GitHub 仓库来源，`--skill r-doc` 用于选择仓库内的技能目录：

```bash
npx skills add riesaexe/r-doc --list
npx skills add riesaexe/r-doc --skill r-doc -g -y
npx skills list -g
```

如果验证的是其他仓库或 fork，再把 `riesaexe/r-doc` 替换为对应的 `<owner>/<repo>`；不要把 `r-doc` 单独作为仓库来源。

若只想安装到当前项目，去掉 -g。如果需要指定代理，可增加 -a codex、-a claude-code 或其他受支持的代理名称。

安装验证至少确认：

- CLI 能发现 r-doc；
- 安装后目标代理能读取 r-doc/SKILL.md；
- references/ 文件没有被遗漏；
- scripts/ 和 tests/ 能在干净环境运行；
- 全局安装副本与公开源版本一致。

## SkillHub 导入

GitHub 公开发布并完成 npx 安装验证后，将公开 GitHub 仓库地址手动导入 SkillHub。SkillHub 只作为分发入口，不作为源文件事实源；任何修复先提交 GitHub，再重新导入或刷新平台条目。

## 参考

- [Vercel Labs skills CLI README](https://github.com/vercel-labs/skills/blob/main/README.md)
- [Vercel Labs skills CLI](https://github.com/vercel-labs/skills)
