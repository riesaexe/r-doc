# GitHub 与 npx skills 发布指南

## 目标结构

Vercel Labs 的 skills CLI 通过 GitHub 或其他 Git 源安装 Skill。公开仓库应保留以下路径：

~~~text
<repository-root>/
├── skills/
│   └── r-doc/
│       ├── SKILL.md
│       ├── agents/
│       ├── references/
│       └── assets/
├── README.md
├── LICENSE
└── CHANGELOG.md
~~~

SKILL.md 的 frontmatter 至少包含 name 和 description。r-doc 的源目录已经符合 skills/r-doc/SKILL.md 约定。

## 本地发现检查

在仓库根目录运行：

~~~bash
npx skills add . --list
~~~

输出中应能看到 r-doc。这个命令只用于列出发现结果，不代表已经完成公开发布。

## GitHub 发布

公开发布前需要确定 GitHub owner/repository、默认分支和许可证。准备完成后：

1. 在本地初始化或连接 Git 仓库；
2. 提交 skills/r-doc、README、docs、VERSION、CHANGELOG 和 LICENSE；
3. 推送默认分支到公开 GitHub 仓库；
4. 创建与 VERSION 一致的版本标签，例如 v0.1.0；
5. 创建 GitHub Release，附上变更说明和必要的发布包；
6. 从公开仓库地址执行 npx 安装验证。

## npx skills 安装验证

将占位符替换为实际仓库后：

~~~bash
npx skills add <owner>/<repo> --list
npx skills add <owner>/<repo> --skill r-doc -g -y
npx skills list -g
~~~

若只想安装到当前项目，去掉 -g。如果需要指定代理，可增加 -a codex、-a claude-code 或其他受支持的代理名称。

安装验证至少确认：

- CLI 能发现 r-doc；
- 安装后目标代理能读取 r-doc/SKILL.md；
- references/ 文件没有被遗漏；
- 全局安装副本与公开源版本一致。

## SkillHub 导入

GitHub 公开发布并完成 npx 安装验证后，将公开 GitHub 仓库地址手动导入 SkillHub。SkillHub 只作为分发入口，不作为源文件事实源；任何修复先提交 GitHub，再重新导入或刷新平台条目。

## 参考

- [Vercel Labs skills CLI README](https://github.com/vercel-labs/skills/blob/main/README.md)
- [Vercel Labs skills CLI](https://github.com/vercel-labs/skills)
