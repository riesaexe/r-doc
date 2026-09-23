---
name: r-doc
description: "Govern documentation with bounded safe reads for public, interface, config, architecture, release, or docs changes; protect .env/secrets and skip unrelated code-only refactors."
metadata:
  version: "1.0.0"
---

# r-doc: Project documentation governance

## Purpose

Maintain project documentation as a navigable, reviewable knowledge base with low context cost: have maintainers or AI agents read the project-root `AGENTS.md` first, then load only the minimum document set required for the current task through the indexes.

This is a project-level documentation standard, not a business-code implementation standard. The project's documentation hierarchy never overrides system instructions, the user's current request, or higher-level tool rules.

## When to use

Use this skill automatically in the following situations, or whenever the user explicitly invokes `$r-doc`:

- Initializing a project, organizing project knowledge, or completing missing documentation entry points;
- Working with plans, requirements, design, architecture decisions, APIs, testing, releases, deployment, rules, or process documents;
- Changing code, configuration, interfaces, data models, processes, deployment, or architecture;
- Checking documentation synchronization during code review, before merging, before release, or during maintenance;
- Finding missing, stale, duplicated, conflicting, broken, or incorrectly loaded documentation.

Do not start the full documentation-governance workflow for a purely local code refactor that does not affect public behavior, data, configuration, architecture, or project rules.

## Activation gate

Implicit activation is intentionally supported, but apply this gate before doing substantial work. Continue only when at least one condition is true:

- The user explicitly invokes `$r-doc` or asks for documentation governance;
- The task creates or changes public behavior, interfaces, configuration, data formats, architecture, processes, deployment, release behavior, or project rules;
- The task asks to initialize, index, audit, repair, synchronize, review, or publish project documentation.

Do not turn an unrelated code edit into a documentation project merely because the repository contains `AGENTS.md` or `docs/`.

## Bounded and safe reading

Use a bounded, deny-by-default reading plan. Enumerate paths without opening their contents, using tools such as `rg --files` or `Get-ChildItem`; then read only named files or explicit source, documentation, and test directories required by the task.

- Before inspecting Git changes, list paths and statuses with `git status --short` and tracked changed paths with `git diff --name-only`. Classify paths first, exclude protected paths, then read diffs only for explicit safe paths related to documentation impact (for example, `git diff -- docs/api.md src/public_interface.py`). Never use an unrestricted `git diff` when changed paths could include protected files.
- Do not run content searches from `.` or the whole project root. Prefer a narrow search such as `rg -n 'term' src docs tests` and add exclusions explicitly when a broader scope is unavoidable.
- Do not use `rg --hidden` or equivalent whole-tree content scans for convenience. Inspect hidden directories only when the task names a specific path, such as `.agents/notes/`.
- Treat `.env`, `.env.*`, `secrets.*`, credential files, private keys, certificates, and files or directories whose names identify secrets as protected. Do not open, concatenate, execute, or pass them to search, test, or build commands. If the task appears to depend on one, report the path without its contents and request explicit direction.
- Never combine a known safe file read with a wildcard or recursive content read. Keep `AGENTS.md`, indexes, and target files as separate, explicit reads.

Path enumeration is not content reading, but a command that searches or prints file contents must still obey these boundaries.

## Non-negotiable constraints

1. Scope work to the project root. Prefer the Git root; for non-Git projects, use the project root explicitly identified by the user.
2. Apply the selected governance level. `AGENTS.md` remains the project entrypoint; `docs/README.md`, nested indexes, and topic metadata are required only at the `standard` or `strict` level. Keep link and sensitive-content checks at every level.
3. Keep `AGENTS.md` limited to the project overview, scope, quick start, context-loading order, key directories, commands, mandatory rules, prohibitions, and task routes. At `standard` and `strict`, include the `docs/` index; at `minimal`, link directly to the few maintained documents instead.
4. Keep each topic document focused on one subject. Split mixed, hard-to-locate, or overlong topics. Do not create empty documents just to fill a directory.
5. Keep documentation synchronized with code, configuration, interfaces, processes, deployment, and decision changes. Record important constraints, pitfalls, and non-obvious decisions.
6. Never write secrets, tokens, passwords, sensitive personal information, or real values that could bypass security controls. Stop writing and report suspected sensitive information.
7. Merge non-destructively when `AGENTS.md`, `docs/`, or existing documents are present: preserve facts and history instead of overwriting or deleting them. Report conflicts and propose a single source of truth.
8. By default, modify only documents, indexes, templates, metadata, and documentation comments. Read code and Git diffs only to determine documentation impact; do not modify business code.
9. Do not treat file existence as documentation completion. Check indexes, links, status, relationships, and consistency of affected content.

## Standard workflow

Choose the project governance level and task-impact workflow separately. A lower governance level reduces documentation scaffolding; it never disables safe-reading, link-target, sensitive-content, preservation, or conflict checks.

### Project governance levels

| Level | Use when | Required structure |
| --- | --- | --- |
| `minimal` | A personal repository or a small project with a few maintained documents. | Keep a concise root `AGENTS.md`. Link relevant documents directly from it. `docs/README.md`, nested indexes, and frontmatter are optional. |
| `standard` | The default for shared projects and ongoing maintenance. | Require root `AGENTS.md`, the configured documentation-root `README.md`, nested `README.md` indexes for topic directories, and parent/child navigation. |
| `strict` | Long-lived team, release-critical, or high-assurance documentation. | Use the standard structure, configure required document types, relationships, and lifecycle gates, and treat audit warnings as failures. |

Set `governance_level: minimal`, `governance_level: standard`, or `governance_level: strict` in `.r-doc.yaml`; without it, use `standard`. The audit and repair helpers honor the selected level. In `minimal`, audit still checks links and sensitive content, and every maintained document must be reachable directly from `AGENTS.md` or an existing index.

### Task impact and authorization

| Impact | Typical scope | Workflow |
| --- | --- | --- |
| Low | A typo, one topic update, or mechanical index/link/date repair with established facts. | Read the relevant entrypoint and target only; make the requested change and run the relevant check. |
| Medium | A bounded public-interface, configuration, process, or cross-document change. | Summarize the impact and affected documents, inspect only relevant safe diffs and sources, then update and verify. |
| High | A broad initialization or audit, conflicting sources of truth, sensitive-data handling, release decisions, or consequential moves/archives. | Inventory affected paths and evidence, outline the proposed changes, and pause only for a material ambiguity or an action beyond the user's authorized scope. |

An explicit request to change named documentation, or to repair the documented issue, authorizes that work and the mechanical index/link changes it requires. State the scope and proceed without a separate plan-confirmation turn. Ask only when a fact, target scope, or consequence is materially unclear; do not turn a status update or focused plan into a permission gate.

1. Identify the current development stage, task scope, and document types that may be affected.
2. Read the project-root `AGENTS.md` if it exists, the documentation-root index when required by the selected governance level, relevant nested indexes if present, project-level `.r-doc.yaml`, and documents directly related to the task.
3. Inspect project structure and list changed paths/status first. Exclude protected paths before reading any diff; inspect only explicit safe diffs and relevant code needed to determine documentation impact.
4. Build a document inventory and mark missing, stale, unindexed, broken, status-invalid, duplicated, conflicting, or suspiciously sensitive content.
5. Resolve only material ambiguities. Give a concise scope/plan update before broad work, but do not wait for another confirmation when the user has already authorized the change.
6. Create or update entrypoints, indexes, topic documents, metadata, and project configuration within the authorized scope. Apply safe mechanical repairs in the same task after reviewing the preview; ask only if it exposes a semantic conflict or out-of-scope change.
7. Run the deterministic helpers in `scripts/` when the target environment can execute them. At minimum, run `audit_docs.py --root <project-root>`; use `--strict` for release or merge gates. If a helper cannot run, perform the equivalent checks and report the limitation.
8. Verify context-loading order, required index coverage, links, applicable metadata, relationships, stage gates, and sensitive-content checks.
9. Produce a governance report covering scope, findings, completed updates, blockers, non-blockers, verification evidence, and whether the current stage gate is satisfied.

For stage checklists, read [references/lifecycle-checklists.md](references/lifecycle-checklists.md). For the complete operating workflow, read [references/workflow.md](references/workflow.md).
For deterministic checks and temporary-project QA, read [references/verification.md](references/verification.md).
For safe structural repairs, read [references/repair.md](references/repair.md). For concrete scenarios and common pitfalls, read [references/examples.md](references/examples.md) and [references/pitfalls.md](references/pitfalls.md).
For version-to-version adoption notes, read [references/migration-matrix.md](references/migration-matrix.md).
For cross-agent behavior evaluation, read [references/agent-evaluation.md](references/agent-evaluation.md) and run its evidence validator when evaluation artifacts are available. Package tests do not replace transcript-and-diff evaluation against a real agent.

## 60-second path

1. Use `$r-doc` when explicitly invoked or when the request itself has documentation impact; do not ask for a separate activation confirmation when the scope is clear.
2. Read `AGENTS.md`, the documentation-root index when required by the selected governance level, and the relevant topic index if present.
3. Preview safe structural repairs with `python scripts/repair_docs.py --root <project-root>`.
4. If the request authorizes the documentation repair and the preview contains only safe mechanical changes, apply the displayed repairs with `--apply` in the same task, then run `audit_docs.py --strict`. Do not ask for a second confirmation. Pause only for a material scope, fact, or risk ambiguity.
5. Report automated results separately from semantic conflicts and decisions that still need confirmation.

## Document structure and indexes

Use this default structure and preserve a reasonable existing structure whenever possible:

```text
AGENTS.md
docs/
└── README.md
```

This is the `standard` structure. Under `minimal`, keep documents flat where practical and link each maintained document directly from `AGENTS.md`; do not create indexes or metadata solely to satisfy a template. Add topic directories and nested indexes when their navigation value justifies the maintenance cost. At `standard` and `strict`, each topic index defines its scope, lists its documents, states the reading order, and links to its parent and children. When adding, renaming, or moving a maintained document, update the nearest required index in the same change. Use [references/templates/AGENTS.md](references/templates/AGENTS.md) and [references/templates/README.template.md](references/templates/README.template.md) only when the selected level calls for them.

At `standard` and `strict`, use this context-loading order. At `minimal`, start with the root entrypoint and follow its direct links to relevant documents:

```text
AGENTS.md
→ docs/README.md
→ relevant topic README.md
→ target document
→ supplementary documents explicitly linked by the target
```

## Status, relationships, and conflicts

Topic documents normally use this lifecycle:

```text
draft → proposed → active → superseded → archived
```

When documentation disagrees with code, tests, or other documents, state the intended behavior, current behavior, and conflict location. Follow the user's explicit decision when it resolves the conflict. Ask only when the authoritative source or intended behavior remains materially unclear; do not silently rewrite implementation or erase historical evidence.

For metadata rules, read [references/metadata-schema.md](references/metadata-schema.md). For project-level overrides, read [references/project-config.md](references/project-config.md).

## Decision notes

Use the optional decision-note layer for non-trivial changes whose rationale, alternatives, or consequences would otherwise be lost in a commit or scattered across documents. It lives under `.agents/notes/` by convention and is discovered automatically when present; configure `decision_notes.root` when a project uses another in-root location. Notes use `proposed/`, `implemented/`, `rejected/`, or `archived/` lifecycle directories and one class directory such as `architecture/`, `feature/`, or `testing/`. The deterministic audit checks their frontmatter, lifecycle path, required sections, links, relationships, and sensitive content, but does not require a central high-churn index. Search existing notes before proposing a related decision, update the owning note when the decision remains the same, and create a linked successor when the decision reverses or materially changes.

Read [references/decision-notes.md](references/decision-notes.md) for the trigger boundary, format, lifecycle, and maintenance workflow. Use [references/templates/decision.md](references/templates/decision.md) only after confirming that a decision note is warranted.
For lifecycle operations, use `python scripts/decision_notes.py archive <note-path>` to preview an archive move. If the user's request authorizes that archive and the preview matches the requested scope, add `--apply` in the same task; otherwise ask only when the target or consequences are materially unclear. Supersession links and cycles are checked by the normal audit.

## Minimum report standard

Every final governance report must include:

```text
Current stage and inspection scope
Findings (missing, stale, conflicting, broken, or sensitive content)
Completed documentation updates
Remaining blockers and non-blockers
Verification methods and results
Current documentation stage gate: satisfied / not satisfied
```

Use templates only when they reduce repeated work. Read [references/templates/README.md](references/templates/README.md) first, then choose a template for the project type and current task. Do not generate batches of empty documents.
