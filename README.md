<p align="center">
  <img src="skills/r-doc/assets/r-doc.svg" alt="r-doc 图标" width="128" height="128">
</p>

<h1 align="center">r-doc</h1>

<p align="center">
  <strong>自动管理开发文档，持续贯彻治理规范。</strong><br>
  面向 AI 代理与人类维护者，让每一次需求、设计、接口和发布变更，都留下准确、可查、可维护的项目知识。
</p>

<p align="center">
  <a href="https://github.com/riesaexe/r-doc">GitHub</a>
  ·
  <a href="https://github.com/riesaexe/r-doc/releases/latest">最新版本</a>
  ·
  <a href="https://github.com/riesaexe/r-doc/blob/main/LICENSE">MIT License</a>
</p>

<p align="center">
  <code>AGENTS.md</code>
  ·
  <code>docs/</code>
  ·
  <code>npx skills</code>
</p>

---

r-doc 不是一次性的文档生成器，而是开发过程中的文档治理层。它在初始化、开发变更、代码审查和发布检查中，自动建立入口、维护索引、追踪文档影响，并在发现缺失、过时、重复、冲突或断链时给出明确反馈。

## 从计划到发布，文档始终在治理范围内

| 开发场景       | r-doc 自动完成                                                               |
| -------------- | ---------------------------------------------------------------------------- |
| 初始化项目     | 建立 `AGENTS.md`、`docs/README.md` 和主题索引，让资料有入口、有位置。        |
| 需求与开发变更 | 检查需求、设计、接口、配置、测试、部署等文档是否需要同步。                   |
| 审查与发布     | 发现缺失、过时、重复、冲突和断链；记录关键决策与风险，必要时暂停并请求确认。 |

r-doc 管理的是开发过程中的文档与知识，不替代业务代码实现；默认只维护文档、索引、元数据和文档注释。

## 适合什么时候使用

- 开始一个新项目，需要建立文档入口；
- 需求、设计或架构发生变化；
- 新增或修改公共接口、配置、数据格式或部署流程；
- 代码审查、合并或发布前需要确认文档是否同步；
- 项目文档难以查找、互相矛盾或已经过时。

## 安装

从本项目的公开 GitHub 仓库安装 r-doc：

```bash
npx skills add riesaexe/r-doc --skill r-doc -g -y
```

只安装到当前项目时，去掉 -g：

```bash
npx skills add riesaexe/r-doc --skill r-doc -y
```

也可以指定目标代理：

```bash
npx skills add riesaexe/r-doc --skill r-doc -a codex -y
```

这里的 `riesaexe/r-doc` 是 GitHub 仓库来源，`--skill r-doc` 是仓库内的技能目录名；它们不是同一个参数。只有在安装其他仓库或你自己的 fork 时，才需要把仓库来源替换为对应的 `<owner>/<repo>`。

## 使用

安装后，可以直接提出自然语言需求，也可以显式调用 r-doc：

```text
$r-doc 初始化这个项目的 AGENTS.md 和 docs/ 文档结构。

$r-doc 检查这次 API 变更需要同步哪些文档。

$r-doc 审查发布前的需求、设计、测试和部署文档是否一致。
```

## 管理的文档结构

```text
AGENTS.md
docs/
└── README.md
```

AGENTS.md 是项目级入口和导航；详细知识放在 docs/，每篇文档聚焦一个主题。复杂主题可以建立子目录，并使用 README.md 说明范围、阅读顺序和文档列表。

## 安全与维护原则

- 保留已有项目知识，发现冲突时先报告；
- 不把当前实现自动改写成期望规范；
- 不写入密钥、令牌、密码或敏感个人信息；
- 默认只维护文档、索引、元数据和文档注释，不修改业务代码；
- 文档未同步时，不把当前开发阶段宣布为已完成。
