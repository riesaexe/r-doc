<p align="right"><a href="README.zh-CN.md">中文</a></p>

<p align="center">
  <img src="skills/r-doc/assets/r-doc.svg" alt="r-doc icon" width="128" height="128">
</p>

<h1 align="center">r-doc</h1>

<p align="center">
  <strong>Make documentation work like code—with standards, versioning, traceability, and governance gates.</strong><br>
  A documentation-governance skill for AI agents and human maintainers that turns project knowledge into verifiable, maintainable, continuously evolving engineering assets.
</p>

<p align="center">
  <a href="https://github.com/riesaexe/r-doc">GitHub</a>
  ·
  <a href="https://github.com/riesaexe/r-doc/releases/latest">Latest release</a>
  ·
  <a href="https://github.com/riesaexe/r-doc/blob/main/LICENSE">MIT License</a>
</p>

<p align="center">
  <a href="https://github.com/riesaexe/r-doc/actions/workflows/quality.yml">
    <img src="https://github.com/riesaexe/r-doc/actions/workflows/quality.yml/badge.svg" alt="Quality checks">
  </a>
</p>

<p align="center">
  <code>Standards first</code>
  ·
  <code>Traceable changes</code>
  ·
  <code>Verifiable facts</code>
  ·
  <code>Visible risk</code>
</p>

<p align="center">
  <a href="https://skills.sh/riesaexe/r-doc">
    <img src="https://skills.sh/b/riesaexe/r-doc" alt="r-doc on skills.sh">
  </a>
</p>

---

## Get started in 30 seconds

Install r-doc globally:

```bash
npx skills add riesaexe/r-doc --skill r-doc -g -y
```

Then use natural language, or invoke `$r-doc` explicitly:

| Goal                  | Example request                                                                       |
| --------------------- | ------------------------------------------------------------------------------------- |
| Initialize governance | `$r-doc Initialize this project's AGENTS.md and docs/ structure.`                     |
| Check change impact   | `$r-doc Check which documents need to be synchronized for this API change.`           |
| Audit before release  | `$r-doc Audit the requirements, design, testing, and deployment docs before release.` |

## Core philosophy

Documentation is not an attachment to the codebase. It is an engineering asset. Requirements define what to build, design explains how to build it, APIs and tests define how to verify it, and release and deployment documents define how to deliver it. Without a shared entry point, explicit status, and change history, that knowledge cannot reliably support a team or an AI agent.

r-doc is not a one-off document generator. It is a governance layer for the development process: during initialization, development changes, code review, and release checks, it automatically establishes entry points, maintains indexes, traces documentation impact, and reports missing, stale, duplicated, conflicting, or broken content.

> Define the standard before the change. Record facts before making judgments. Surface conflicts before they become history.

## What `0.2.0` adds

The latest release makes documentation governance more actionable and less dependent on an agent remembering every rule:

| Capability | What it does | Safety boundary |
| --- | --- | --- |
| Safe structural repair | Previews and, after confirmation, creates missing entrypoints, nested indexes, and missing index links. | Never overwrites, deletes, moves, or guesses through a conflict. |
| Deterministic checks | Audits links, index coverage, metadata, duplicate IDs, sensitive-value patterns, and Skill package structure. | Structural checks do not replace semantic review. |
| Real workflow guidance | Includes initialization, API-change, release-audit, topic-directory examples, and a dedicated pitfalls guide. | Load only the references relevant to the current task. |
| Release quality gates | Runs tests and validation in CI, with a reproducible temporary-project QA path. | A green check does not declare unresolved product decisions complete. |

## What `0.2.1` adds

This patch tightens the deterministic governance layer for real project metadata and multiple development platforms:

| Capability | What it does | Safety boundary |
| --- | --- | --- |
| Real YAML frontmatter | Parses nested mappings and lists with a safe YAML loader and reports malformed frontmatter explicitly. | Parser errors are findings; a passing audit is not semantic approval. |
| Broader secret baseline | Checks JWTs, OpenAI keys, credentialed database URLs, and generic password assignments in addition to common provider tokens. | It is a deterministic baseline, not a complete secret scanner. |
| Cross-platform quality gate | Exercises Ubuntu and Windows on pinned Python 3.10–3.13 versions. | CI compatibility does not replace validation on a project's own runtime. |

## What `0.2.2` adds

This patch closes two small but important governance blind spots:

| Capability | What it does | Safety boundary |
| --- | --- | --- |
| Chinese placeholder awareness | Recognizes common Chinese placeholders such as `你的密码`, `请输入你的密码`, and `示例口令` without hiding real Chinese password values. | The baseline remains finite and does not replace a full secret scanner. |
| Self-hosted parser dogfood | Uses nested mapping and list frontmatter in r-doc's own verification record, so the repository exercises the parser it ships. | Passing the dogfood check proves parsing coverage, not semantic approval of arbitrary metadata. |

## What `0.2.3` adds

This release turns more of the governance contract into executable, reviewable checks:

| Capability | What it does |
| --- | --- |
| Executable project configuration | Applies `.r-doc.yaml` to the documentation root, exclusions, required document types, document-type relationships, and lifecycle gates. |
| Bidirectional navigation | Verifies the root entrypoint, documentation index, and nested indexes can navigate both downward and back to their parent. |
| Deterministic link coverage | Checks inline, reference-style, and parenthesized Markdown links after resolving paths and rejecting project-root escapes. |
| Metadata relationships | Checks document IDs, `related_docs`, `supersedes`, review dates, title headings, and creation/update order. |

The release keeps semantic decisions and real-agent behavior evaluation explicit: deterministic checks provide evidence, but they do not replace human or agent-level judgment.

## What `0.2.5` adds

This release closes the remaining audit blind spots identified through adversarial review:

| Improvement | What it does | Safety boundary |
| --- | --- | --- |
| Root Markdown coverage | Audits directly maintained root files such as `README.md`, `CONTRIBUTING.md`, and `SECURITY.md` for broken links and sensitive values. | Metadata and index coverage remain scoped to the configured documentation root. |
| Complete link semantics | Checks image targets for existence, while unused reference definitions and images stay out of the navigation graph; nested indexes must link to direct parents and children. | Asset existence checks do not claim that an image's visual content is correct. |
| Stronger metadata and gates | Validates existing `related_code` files, successor relations and backlinks for `superseded` documents, and rejects unconfigured `--stage` values. | Structural evidence still does not replace semantic review. |
| Safer examples | Allow-lists the exact public AWS sample `AKIAIOSFODNN7EXAMPLE` without disabling scans for other fenced code. | This is a narrow exception, not a general code-block exemption. |

The release is backed by 38 regression tests and the package, repair-preview, strict-audit, and Skill validator gates used for earlier releases.

## What `0.2.4` adds

This hardening release closes the remaining small gaps identified after `0.2.3`:

| Improvement | What it does |
| --- | --- |
| De-duplicated findings | Collapses identical findings from multiple audit phases, keeping symlink and unreadable-file reports actionable instead of noisy. |
| Existing-project migration guidance | Explains how to adopt bidirectional navigation with preview-first repairs, without rewriting topic content. |
| Verification coverage map | Documents the deterministic coverage for configuration, navigation, links, metadata relationships, and sensitive content. |

The release is backed by 27 regression tests and the same package, repair-preview, strict-audit, and Skill validator gates used for earlier releases.

For a repository maintainer, the guarded repair flow is:

```text
$r-doc Preview safe documentation repairs. Do not write files yet.
Review the plan, then apply only the safe structural repairs and run a strict audit.
```

The executable helpers are also available in the source repository:

```bash
python -m pip install -r requirements-dev.txt
python skills/r-doc/scripts/repair_docs.py --root .
python skills/r-doc/scripts/repair_docs.py --root . --apply
python skills/r-doc/scripts/audit_docs.py --root . --strict
```

Read the [safe repair guide](skills/r-doc/references/repair.md), [practical examples](skills/r-doc/references/examples.md), and [common pitfalls](skills/r-doc/references/pitfalls.md) for the full boundaries.

## Why r-doc

| Governance principle   | How r-doc applies it                                                                                                                                                              |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Standards first        | Use `AGENTS.md` as the project entry point and `docs/README.md` plus topic indexes to organize knowledge. Use status, metadata, and lifecycle rules to keep documents actionable. |
| Traceable changes      | When code, configuration, APIs, processes, deployment, or architecture changes, identify the affected planning, design, testing, release, and operations documents.               |
| Single source of truth | Preserve existing facts, surface conflicts between code and docs or between documents, and never silently replace current behavior with an intended standard.                     |
| Explicit risk          | Report missing, stale, duplicated, conflicting, broken, or suspiciously sensitive content. Pause and ask for confirmation when the risk is material.                              |
| Minimal context        | Load `AGENTS.md` → `docs/README.md` → the relevant topic index → the target document, so agents use only the context needed for the task.                                         |

## The governance loop from planning to release

| Development stage         | Automated governance focus                                                                                             | Delivery outcome                                                                        |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Planning and requirements | Establish entry points for plans, requirements, and scope; make the current stage and completion gates explicit.       | The team knows what to build and what cannot yet be called complete.                    |
| Design and implementation | Record design, architecture decisions, APIs, configuration, and constraints; analyze documentation impact.             | Decisions have context, and knowledge does not remain trapped in a chat.                |
| Testing and review        | Check implementation, tests, docs, and indexes for consistency; expose gaps and conflicts.                             | Problems are visible before delivery instead of being reconstructed after launch.       |
| Release and deployment    | Synchronize release notes, migration steps, deployment procedures, and known limitations; recheck documentation gates. | A release has more than a version number: it has reviewable facts and clear boundaries. |

## How it differs from one-off document generation

| One-off generation                               | r-doc governance                                                         |
| ------------------------------------------------ | ------------------------------------------------------------------------ |
| Generate a document that looks complete          | Maintain a navigable, indexed, reviewable knowledge base                 |
| The document goes stale when the task ends       | Check documentation impact and synchronization on every relevant change  |
| Treat file existence as completion               | Check indexes, links, status, relationships, and stage gates             |
| Overwrite or guess when facts conflict           | Preserve facts, report conflicts, and propose decisions for confirmation |
| Ask the AI to read the entire repository context | Use indexes to load the minimum context required for the task            |

## When to use it

- Starting a project and establishing its documentation entry points;
- Changing requirements, design, architecture, public APIs, configuration, data formats, or deployment;
- Reviewing or merging work that may affect project knowledge;
- Auditing documentation before a release;
- Finding missing, stale, duplicated, conflicting, or hard-to-navigate project documents.

r-doc governs development documentation and knowledge. It does not replace business-code implementation; by default, it maintains documents, indexes, metadata, and documentation comments without changing business code.

## See it in action

Initialize an existing repository:

```text
$r-doc Inspect this repository and establish its AGENTS.md and docs/ knowledge base. Preserve existing facts, report conflicts, and show the files changed.
```

When an API changes, ask for an impact pass before implementation is considered complete:

```text
$r-doc The public POST /users response now includes `role`. Trace the documentation impact, update the relevant API and testing documents, and report anything that still needs confirmation.
```

Before release, make the governance result explicit:

```text
$r-doc Audit the release documentation. Check indexes, links, metadata, stale claims, deployment steps, and known limitations. Do not silently rewrite conflicting facts.
```

Typical results are a maintained `AGENTS.md`, updated topic indexes, synchronized documents, and a concise report of missing or conflicting facts. r-doc does not infer a release decision when evidence is incomplete.

### A small project example

Before governance:

```text
checkout-service/
├── README.md
├── src/
└── tests/
```

Ask r-doc to inspect the repository and preview safe repairs. After confirmation, the result is a navigable skeleton:

```text
checkout-service/
├── AGENTS.md
├── docs/
│   └── README.md
├── README.md
├── src/
└── tests/
```

The generated files only establish navigation. You still add project-specific commands, rules, requirements, and decisions; r-doc will then keep those documents indexed and report structural or semantic gaps.

## Troubleshooting

| Situation | What to ask |
| --- | --- |
| The skill did not activate | Use `$r-doc` explicitly and describe the documentation or governance change. Code-only edits with no documentation impact are intentionally out of scope. |
| A document is reported as unindexed | Ask r-doc to update the nearest `README.md` index and preserve the document's existing content. |
| Existing docs conflict with code | Ask for an evidence report first; confirm which source is authoritative before changing either side. |
| You need Chinese output | Ask for Chinese documentation or specify the target document language. Runtime rules remain in `SKILL.md`. |
| Release checks fail | Run the repository's validation commands and inspect the reported path, link, metadata, or sensitive-content finding before retrying. |
| An existing project fails `missing-navigation-link` after upgrading | Preview the safe repair, confirm the entrypoint and parent-index targets, apply the links, then rerun a strict audit. This rule does not rewrite topic content. |

## Installation options

Install only in the current project by removing `-g`:

```bash
npx skills add riesaexe/r-doc --skill r-doc -y
```

Target a specific agent:

```bash
npx skills add riesaexe/r-doc --skill r-doc -a codex -y
```

Here, `riesaexe/r-doc` is the GitHub repository source and `--skill r-doc` selects the skill directory inside that repository. They are different arguments. Replace the repository source with `<owner>/<repo>` only when installing a different repository or your own fork.

## Project structure

```text
AGENTS.md
docs/
└── README.md
```

`AGENTS.md` is the project entry point and navigation layer. Detailed knowledge lives in `docs/`, with each document focused on one topic. Complex topics can use subdirectories with a `README.md` that defines scope, reading order, and document links.

## Safety and maintenance principles

- Preserve existing project knowledge and report conflicts before changing facts;
- Do not rewrite current implementation into an intended standard;
- Never write secrets, tokens, passwords, or sensitive personal information;
- Default to maintaining docs, indexes, metadata, and documentation comments, not business code;
- Do not declare a development stage complete while its documentation remains unsynchronized.
