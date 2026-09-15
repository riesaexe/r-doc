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

## What `0.2.15` adds

This release makes the empirical benchmark output auditable and directly comparable:

| Improvement | What it does | Safety boundary |
| --- | --- | --- |
| Structured trace gate | Parses JSONL, binds trace metadata to `run.json`, derives prompt, activation, selected skill, reports, final response, diff, review, paths, reads, commands, and writes, and cross-checks every field against `evidence.json`. | A trace placeholder, undeclared event field, or evidence-only run cannot pass the benchmark gate; this checks structure and consistency, not cryptographic provenance. |
| Paired condition analysis | Keeps profile metrics condition-aware and emits matched `agent + model + run_id` deltas with mean, median, standard deviation, 95% Student-t intervals, and separate trend/statistical/strong-evidence readiness. | Three pairs only establish a trend; use at least five pairs for the statistical gate and ten for a stronger claim. |
| Read policy metrics | Separates required, allowed, and forbidden reads so legitimate dependency reads do not inflate `unnecessary_reads`. | Case files must declare the allowed set and keep it disjoint from forbidden reads. |
| Audit sample reporting | Raises the performance harness default to ten iterations and records interpolated p95, maximum, and low-sample metadata. | Wall-clock values remain local trend data, not a CI threshold or complexity guarantee. |

The checked-in benchmark summary now contains three valid matched local Codex `gpt-5.5` pairs. It is trend-ready but not statistical-ready: the observed mean task-success delta is `0.0pp`, unnecessary-read delta is `-0.67`, and the 95% intervals remain wide at `n=3`. This is real evidence for observing behavior, not a claim that r-doc already improves success reliably.

## What `0.2.13` adds

This release makes the GitHub-facing documentation language-aware and keeps the two public entrypoints aligned:

| Improvement | What it does | Safety boundary |
| --- | --- | --- |
| Paired public references | Adds Chinese counterparts for the safe-repair guide, practical examples, and common-pitfalls guide. | English references remain canonical for runtime terminology; localized pages cross-link to their English source. |
| Language-specific README routing | Keeps `README.md` on English references and routes `README.zh-CN.md` to `.zh-CN.md` references. | A language switch never silently lands in the other language's user-facing guide. |
| Localization regression guard | Tests that both README link sets exist and target the expected language suffix. | The check covers routing and file existence, not translation quality. |

The release is backed by 68 regression tests, package validation, repair-preview, strict-audit, the official Skill validator, and the public-documentation routing check.

## What `0.2.12` adds

This release moved evaluation from schema readiness toward empirical measurement:

| Improvement | What it does | Safety boundary |
| --- | --- | --- |
| Real benchmark contract | Adds `benchmarks/` run metadata, captured-trace requirements, validated results, and profile aggregation for r-doc and no-r-doc conditions. | No real Agent score is claimed until captured evidence and trace files are present. |
| Bound machine rules | Binds every `machine_rules` check identifier to a code registry and rejects additions, removals, or renames on either side. | The binding proves rule wiring, not semantic correctness of a model's interpretation. |
| Audit performance baseline | Measures 100, 1000, and 5000 Markdown-document fixtures with median and p95 wall-clock times. | Measurements are local trend data, not a CI hard threshold. |

The first benchmark summary is intentionally `pending` until real Codex runs and a no-r-doc baseline are captured.

## What `0.2.11` adds

This maintenance update makes Agent evaluation evidence directly runnable and makes machine scoring rules explicit:

| Improvement | What it does | Safety boundary |
| --- | --- | --- |
| Complete evidence example | Adds a full eight-scenario evidence file that passes the bundled evaluator, instead of presenting disconnected JSON fragments. | The checked-in example is a schema fixture; real evaluations must replace synthetic prompts, reports, and diffs with captured agent artifacts. |
| Declarative machine rules | Records each machine dimension's input checks and pass conditions in `evals/cases.json`, and validates the rule contract before scoring. | Rule descriptions do not claim semantic correctness beyond the listed observable checks. |
| Example regression test | Runs the complete evidence example through the evaluator as part of the test suite. | Documentation examples cannot silently drift from the executable schema. |

This release is backed by the existing regression suite plus a validator test for the complete evidence example and is published from the validated `v0.2.11` tag.

## What `0.2.10` adds

This maintenance update makes Agent evaluation evidence more observable and less self-reported:

| Improvement | What it does | Safety boundary |
| --- | --- | --- |
| Checked paths vs. read files | Records existence or routing checks in `paths_checked`, separately from files whose contents were actually read. | An absent `AGENTS.md` or `docs/` path is no longer misrepresented as a file read. |
| Ordered command evidence | Replaces unordered required-command matching with `required_command_sequence` and requires integer `exit_code: 0` in the declared order. | Failed exploratory commands may remain in the trace, but required commands must succeed. |
| Evidence-derived scorecard | Derives activation, deterministic verification, safety, and repair discipline from captured evidence; human review dimensions require a written basis. | The runner still does not claim to infer semantic preservation or conflict quality automatically. |
| Shared-module regression tests | Adds focused tests for Markdown, path, and security primitives. | Module tests complement, rather than replace, end-to-end audit tests. |

This release is backed by 59 regression tests.

## What `0.2.9` adds

This release makes the shared tooling package safer to consume and keeps Agent evaluation results tied to the Skill version they measure:

| Improvement | What it does | Safety boundary |
| --- | --- | --- |
| Direct submodule imports | Removes eager top-level `rdoc` re-exports so audit, repair, validation, and evaluation load only the modules they use. | Package initialization stays minimal and avoids growing a central import bottleneck. |
| Version-bound evaluation evidence | Adds required `skill_version` to the case file and evidence contract, rejecting missing or mismatched versions. | Scores are comparable only when their tested Skill versions match. |
| Migration and verification sync | Extends the migration matrix and verification record for the 0.2.9 behavior changes. | Upgrades still require preview, strict audit, and review of the recorded evidence. |

The release is backed by 51 regression tests, package validation, repair-preview, strict-audit, the official Skill validator, and the executable evaluation-evidence path.

## What `0.2.8` adds

This maintenance release closes the remaining v0.2.7 review gaps while keeping shared deterministic behavior in one tested package:

| Improvement | What it does | Safety boundary |
| --- | --- | --- |
| Shared tooling package | Moves configuration, finding models, security detectors, Markdown parsing, and anchor generation into `scripts/rdoc/`, reused by audit, repair, validation, and Agent-evidence evaluation. | Entry-point scripts remain explicit; package extraction does not change the governance rules. |
| Broader Agent evaluation | Adds configuration-driven, superseded-document, and Markdown-anchor scenarios to the executable evidence contract. | Evidence still comes from real Agent runs; the validator does not fabricate model behavior. |
| Emoji-safe anchors | Preserves emoji code points when generating heading slugs and adds a regression scenario for links such as `#deploy-🚀`. | The documented contract remains GitHub-compatible and does not infer renderer-specific behavior. |

The release is backed by 50 regression tests, package validation, repair-preview, strict-audit, the official Skill validator, and the executable evaluation-evidence path.

## What `0.2.7` adds

This release closes the remaining edge cases from the v0.2.6 adversarial review and makes adoption evidence easier to verify:

| Improvement | What it does | Safety boundary |
| --- | --- | --- |
| GitHub-compatible anchors | Checks ATX and Setext headings, CJK text, punctuation, consecutive spaces, duplicate-heading suffixes, and explicit HTML `name`/`id` anchors. | The contract is GitHub-compatible; renderer-specific slug rules are not guessed. |
| Visible allowlist evidence | Keeps exact `sensitive_allowlist` matches as informational findings instead of silently hiding them. | Allowlist values must be reviewed public examples, never real credentials. |
| Configuration and migration clarity | Documents all eight project configuration fields, separates frontmatter `planned_code`, and adds a version migration matrix. | Upgrade notes do not rewrite project content automatically. |
| Executable agent-evaluation evidence | Adds eight scenario definitions, including configuration-driven governance, supersession closure, and Markdown anchor validation, plus a validator for prompts, file traces, diffs, reports, commands, and scorecard results. | The validator checks supplied evidence; it does not fabricate model traces. |

The release is backed by 50 regression tests, package validation, repair-preview, strict-audit, the official Skill validator, and the executable evaluation-evidence path.

## What `0.2.6` adds

This release hardens the audit boundary against false positives and project-specific documentation workflows:

| Improvement | What it does | Safety boundary |
| --- | --- | --- |
| Context-aware link parsing | Ignores link-shaped text inside fenced code, inline code, and HTML comments, while still checking real image and reference targets. | Sensitive-value scanning still inspects fenced code. |
| Fragment validation | Verifies that Markdown links point to an existing heading anchor, not only an existing file. | Heading slug matching is deterministic; semantic link intent still needs review. |
| Configurable example exceptions | Adds exact `sensitive_allowlist` entries for reviewed provider documentation examples and expands the baseline to Google `AIza`-style keys. | Exceptions are exact strings, never patterns, and must not contain real credentials. |
| Planning-aware metadata | Adds `planned_code` for future paths while keeping `related_code` strict about existing files. | Planned paths must remain inside the project root. |
| Root-file and test coverage | Documents root Markdown exclusion behavior and separates audit, configuration, and repair regression suites. | Root `AGENTS.md` remains mandatory and always checked. |

The release is backed by 45 regression tests, package validation, repair-preview, strict-audit, and the official Skill validator.

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

## What `0.2.3` adds

This release turns more of the governance contract into executable, reviewable checks:

| Capability | What it does |
| --- | --- |
| Executable project configuration | Applies `.r-doc.yaml` to the documentation root, exclusions, required document types, document-type relationships, and lifecycle gates. |
| Bidirectional navigation | Verifies the root entrypoint, documentation index, and nested indexes can navigate both downward and back to their parent. |
| Deterministic link coverage | Checks inline, reference-style, and parenthesized Markdown links after resolving paths and rejecting project-root escapes. |
| Metadata relationships | Checks document IDs, `related_docs`, `supersedes`, review dates, title headings, and creation/update order. |

The release keeps semantic decisions and real-agent behavior evaluation explicit: deterministic checks provide evidence, but they do not replace human or agent-level judgment.

## What `0.2.2` adds

This patch closes two small but important governance blind spots:

| Capability | What it does | Safety boundary |
| --- | --- | --- |
| Chinese placeholder awareness | Recognizes common Chinese placeholders such as `你的密码`, `请输入你的密码`, and `示例口令` without hiding real Chinese password values. | The baseline remains finite and does not replace a full secret scanner. |
| Self-hosted parser dogfood | Uses nested mapping and list frontmatter in r-doc's own verification record, so the repository exercises the parser it ships. | Passing the dogfood check proves parsing coverage, not semantic approval of arbitrary metadata. |

## What `0.2.1` adds

This patch tightens the deterministic governance layer for real project metadata and multiple development platforms:

| Capability | What it does | Safety boundary |
| --- | --- | --- |
| Real YAML frontmatter | Parses nested mappings and lists with a safe YAML loader and reports malformed frontmatter explicitly. | Parser errors are findings; a passing audit is not semantic approval. |
| Broader secret baseline | Checks JWTs, OpenAI keys, credentialed database URLs, and generic password assignments in addition to common provider tokens. | It is a deterministic baseline, not a complete secret scanner. |
| Cross-platform quality gate | Exercises Ubuntu and Windows on pinned Python 3.10–3.13 versions. | CI compatibility does not replace validation on a project's own runtime. |

## What `0.2.0` adds

The latest release makes documentation governance more actionable and less dependent on an agent remembering every rule:

| Capability | What it does | Safety boundary |
| --- | --- | --- |
| Safe structural repair | Previews and, after confirmation, creates missing entrypoints, nested indexes, and missing index links. | Never overwrites, deletes, moves, or guesses through a conflict. |
| Deterministic checks | Audits links, index coverage, metadata, duplicate IDs, sensitive-value patterns, and Skill package structure. | Structural checks do not replace semantic review. |
| Real workflow guidance | Includes initialization, API-change, release-audit, topic-directory examples, and a dedicated pitfalls guide. | Load only the references relevant to the current task. |
| Release quality gates | Runs tests and validation in CI, with a reproducible temporary-project QA path. | A green check does not declare unresolved product decisions complete. |
