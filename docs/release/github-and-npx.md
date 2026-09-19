---
id: REL-GITHUB-NPX-001
type: guide
status: active
title: GitHub 与 npx skills 发布指南
created: 2026-09-14
updated: 2026-09-19
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

### GitHub Release API 发布规范（必须遵守）

正式 Release 不得通过 GitHub 网页创建、编辑或上传。必须在本机命令行中使用 Git Credential Manager 提供的凭据，直接调用 GitHub REST API：

1. 用 GET /repos/<owner>/<repo>/releases/tags/<tag> 按标签查询现有 Release；
2. 只有返回 404 时才用 POST /repos/<owner>/<repo>/releases 创建 Release；
3. 读取返回的 upload_url，仅上传不存在的版本包附件；
4. 再次 GET Release，确认 draft=false、标签与 VERSION 一致、附件名称和大小正确。

凭据只能在内存变量或受控的临时配置中使用，不能把 git credential fill 的完整输出、PAT、密码或带凭据的 URL 写入终端、日志、提交或报告。一个不泄露凭据的获取方式是：

~~~bash
cred="$(printf 'protocol=https\nhost=github.com\n\n' | git credential fill)"
# 将 cred 解析为仅供 curl 使用的内存变量；不要 echo cred、username 或 password
curl --user "$username:$password" \
  -H 'Accept: application/vnd.github+json' \
  -H 'X-GitHub-Api-Version: 2022-11-28' \
  ...
unset cred username password
~~~

发布脚本必须具备幂等行为：已存在的 Release 或附件应被复用，不应重复创建。网页只允许用于只读查看最终公开结果；本规范不把浏览器操作视为发布成功证据。执行外部发布前仍需取得用户明确授权。

公开发布前需要确定 GitHub owner/repository、默认分支和许可证。准备完成后：

1. 在本地初始化或连接 Git 仓库；
2. 提交 skills/r-doc、README、docs、VERSION、CHANGELOG 和 LICENSE；
3. 推送默认分支到公开 GitHub 仓库；
4. 创建与 VERSION 一致的版本标签，例如 v0.3.0；
5. 创建 GitHub Release，附上变更说明和必要的发布包；
6. 从公开仓库地址执行 npx 安装验证。

## 仓库治理

`main` 应保持分支保护：普通贡献者通过 pull request 合并并至少获得一个批准，dismiss stale reviews，并禁止 force-push 和删除。当前仓库保留这组保护规则，但允许管理员绕过审批门槛执行签名发布；没有配置未经验证的 CI status check。

发布提交应在 GitHub 显示为 `Verified`。这要求提交者的 GPG 或 SSH signing key 同时登记到 GitHub 账户。本机当前 GPG signing probe 已通过，但 GitHub 端的 `Verified` 状态仍须在下一次签名提交上实测。v0.2.15 的公开提交保持原样，不为补签而重写历史。

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

## English guide

### Repository layout

The skills CLI installs a Skill from GitHub or another Git source. Keep this public structure:

```text
<repository-root>/
├── skills/r-doc/
│   ├── SKILL.md
│   ├── agents/
│   ├── references/
│   ├── scripts/
│   ├── tests/
│   └── assets/
├── README.md
├── LICENSE
└── CHANGELOG.md
```

`SKILL.md` must contain at least `name` and `description` in frontmatter. The source directory also carries reproducible validators and tests, which remain part of the public release.

### Local discovery and validation

Run from the repository root:

```bash
python -m pip install -r requirements-dev.txt
npx skills add . --list
python skills/r-doc/scripts/validate_skill.py skills/r-doc
python skills/r-doc/scripts/repair_docs.py --root .
python skills/r-doc/scripts/audit_docs.py --root . --strict
python -m unittest discover -s skills/r-doc/tests -p 'test_*.py'
```

The output should list r-doc. Discovery is not the same as a public release.

### GitHub release

#### Required GitHub Release API workflow

Do not create, edit, or upload a formal Release through the GitHub web UI. From the local command line, use credentials supplied by Git Credential Manager and call the GitHub REST API directly:

1. GET /repos/<owner>/<repo>/releases/tags/<tag> to find an existing Release;
2. only on 404, POST /repos/<owner>/<repo>/releases to create it;
3. use the returned upload_url and upload only a missing versioned asset;
4. GET the Release again and verify draft=false, the tag matches VERSION, and the asset name and size are correct.

Keep credentials in memory or a controlled temporary config only. Never write the complete git credential fill output, a PAT, a password, or a credential-bearing URL to the terminal, logs, commits, or reports. The browser is read-only for checking the final public result and is not evidence of a successful publication. The flow must be idempotent, and explicit user authorization is required before external publication.

1. Confirm the GitHub owner/repository, default branch, and license.
2. Commit `skills/r-doc`, README files, docs, `VERSION`, `CHANGELOG.md`, and `LICENSE`.
3. Push the default branch.
4. Create the tag matching `VERSION`, such as `v0.3.0`.
5. Create a GitHub Release with bilingual notes and any required package.
6. Verify installation from the public repository URL with `npx skills`.

The `main` branch remains protected for normal contributors with pull-request review, one approval, stale-review dismissal, and no force-push or deletion. Administrators may bypass the approval gate for a signed release; the local GPG signing probe passes, and the release commit must still be checked for GitHub's `Verified` badge.

### npx skills installation

```bash
npx skills add riesaexe/r-doc --list
npx skills add riesaexe/r-doc --skill r-doc -g -y
npx skills list -g
```

`riesaexe/r-doc` is the GitHub repository and `--skill r-doc` selects the Skill directory inside it. Replace only the repository source when testing another repository or fork.

Verify that the CLI discovers r-doc, the installed agent can read `r-doc/SKILL.md`, references are present, scripts/tests run in a clean environment, and the global copy matches the validated source.

### SkillHub

Import the public GitHub repository into SkillHub only after GitHub publication and npx installation verification. SkillHub is a distribution surface, not the source of truth; fixes must land in GitHub first.
