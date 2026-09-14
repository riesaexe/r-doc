# 自建 Skill 项目入口

## 项目概览与范围

本项目维护可复用的 Codex Skill。当前主产品是 r-doc：用于在其他项目中建立和持续维护 AGENTS.md 与 docs/ 文档知识库。

项目源文件位于 skills/，全局安装目录 C:/Users/RiESA/.agents/skills/ 只是已验证的运行副本。后续迭代必须先修改项目源文件，再通过发布流程同步安装副本。

## 快速开始

1. 读取本文件和 [docs/README.md](docs/README.md)。
2. 读取 [r-doc Skill 入口](skills/r-doc/SKILL.md) 和与当前任务相关的 references。
3. 只在 skills/r-doc/ 中修改 Skill 源文件。
4. 运行 Skill 校验和临时项目 QA。
5. 发布前更新 VERSION、CHANGELOG.md 和 docs/release/ 中的记录。

## 上下文加载顺序

~~~text
AGENTS.md
→ docs/README.md
→ 与任务相关的 docs 子目录 README.md
→ skills/r-doc/SKILL.md
→ skills/r-doc/references/ 中的相关文档
~~~

## 关键目录

| 路径 | 用途 |
| --- | --- |
| README.md | GitHub 公开说明和安装入口 |
| skills/r-doc/ | r-doc 唯一源文件 |
| docs/design/ | 设计和架构决策 |
| docs/development/ | 开发、验证和同步流程 |
| docs/release/ | 版本、校验、打包和发布流程 |
| CHANGELOG.md | 版本变更记录 |
| VERSION | 当前项目版本 |

## 常用命令

在 Windows 主机上验证 Skill：

~~~powershell
$env:PYTHONUTF8 = '1'
py C:/Users/RiESA/.codex/skills/.system/skill-creator/scripts/quick_validate.py D:/AI/自建skill/skills/r-doc
~~~

## 强制规则

- skills/r-doc/ 是唯一事实源；不要把全局安装目录当作开发源。
- Skill 入口保持精炼；详细规则放在 references/，并从入口按需链接。
- 修改 Skill 行为时同步更新相关开发文档或发布记录。
- 发布前必须通过格式校验、链接检查和临时项目 QA。
- 文档中不得写入密钥、令牌、密码或敏感个人信息。
- 保留已有事实和历史；不直接覆盖或删除未审查的文档内容。

## 禁止事项

- 不在 C:/Users/RiESA/.agents/skills/r-doc/ 中直接开发。
- 不把未经验证的源文件标记为已发布。
- 不为了通过校验删除失败证据、测试或历史记录。
- 不把业务代码、第三方依赖、构建产物或缓存塞入 Skill 源目录。

## 路线指引

- Skill 行为、触发条件或边界：先读 skills/r-doc/SKILL.md。
- 工作流和冲突处理：读 skills/r-doc/references/workflow.md。
- 生命周期门槛：读 skills/r-doc/references/lifecycle-checklists.md。
- 元数据或状态：读 skills/r-doc/references/metadata-schema.md。
- 项目覆盖配置：读 skills/r-doc/references/project-config.md。
- 版本和发布：读 [docs/release/README.md](docs/release/README.md)。
- GitHub、npx skills 和 SkillHub：读 [docs/release/github-and-npx.md](docs/release/github-and-npx.md)。

## docs 总索引

从 [docs/README.md](docs/README.md) 开始，按当前任务进入设计、开发或发布文档。
