# r-doc workflow

## 1. Confirm scope

Prefer `git rev-parse --show-toplevel` to identify the project root. If the current directory is not a Git project, use the project root explicitly named by the user. Do not mistake a personal directory or workspace parent for the project root.

After confirming the project root, read `.r-doc.yaml` when present, then read `AGENTS.md`, the docs-root index when required by the selected level, and relevant topic indexes. Do not read the entire repository just to understand it; use indexes or direct links to select the minimum document set.

Select a project governance level independently from the impact level of the current task. Set `governance_level` in `.r-doc.yaml`; the default is `standard`.

| Level | Suitable projects | Required structure |
| --- | --- | --- |
| `minimal` | Personal repositories and small projects with a few maintained documents. | Keep `AGENTS.md`; link relevant documents directly from it. The docs-root index, nested indexes, and topic frontmatter are optional. |
| `standard` | Shared projects and ongoing maintenance; default. | Require `AGENTS.md`, the docs-root `README.md`, nested indexes for topic directories, and parent/child navigation. |
| `strict` | Long-lived team, release-critical, or high-assurance projects. | Standard structure plus required document types, configured relationships and lifecycle gates; warnings fail the audit. |

All levels retain path-safe reading, link-target validation, and sensitive-content checks. In `minimal`, maintained documents still need a route from `AGENTS.md` or an existing index.

## 2. Inventory documentation

Inventory the non-code material maintained by the project team: plans, requirements, designs, decisions, interfaces, tests, releases, deployments, rules, guides, processes, and records. Exclude by default:

- `.git/`, dependency, vendor, cache, and temporary directories;
- build output, logs, coverage output, and fully generated files that are not hand-maintained;
- source code, test code, and scripts themselves.

Register unknown formats before editing them. Binary documents may be checked for existence, status, index coverage, and relationships. Edit a binary document only when the user's request covers that operation and an appropriate document tool can preserve its format; pause only if the requested change or data-loss risk is materially unclear.

The deterministic audit also scans directly maintained Markdown files in the project root, including `README.md`, `CONTRIBUTING.md`, and `SECURITY.md`, for broken links and sensitive values. `README.md` is included by default, and `.r-doc.yaml` `exclude` applies to root Markdown as well. Metadata, index coverage, and lifecycle relationships remain scoped to Markdown documents under the configured `docs_root`; generated or excluded paths are not scanned. `AGENTS.md` is the mandatory entrypoint and is always checked.

Before reading file contents, apply a bounded read plan: enumerate paths without opening them, choose explicit source/documentation/test roots, and read only named files or those roots. Never use a whole-tree content search from `.` or `rg --hidden` merely to discover the project. Treat `.env`, `.env.*`, `secrets.*`, credential/key/certificate files, and secret-named paths as protected; do not open or pass them to search, test, or build commands. If a task depends on protected content, report the path and request explicit direction. Keep safe entrypoint reads separate from wildcard or recursive content commands.

When reviewing Git changes, first list path names and statuses with `git status --short` and `git diff --name-only`. Classify paths and remove protected paths from the candidate set before reading any diff. Read only explicit safe, relevant paths (for example, `git diff -- docs/api.md src/public_interface.py`); never run an unrestricted `git diff` that could print tracked credentials or secret files.

## 3. Initialize or repair entry points

When entry points are missing, initialize according to the selected level: `minimal` creates only a concise `AGENTS.md`; `standard` or `strict` also creates the docs-root `README.md`. Create topic directories and documents only when the real project needs them. The root entrypoint contains project navigation, common commands, mandatory rules, prohibitions, context-loading order, and task or module routes; at `standard` and `strict`, it links to the docs-root index.

When entry points already exist:

1. Preserve existing facts, constraints, and historical links;
2. At `standard` and `strict`, fill missing navigation and required indexes; at `minimal`, link affected documents directly from the root entrypoint or an existing index;
3. Keep reverse links when moving detail into `docs/` if the selected level requires the index;
4. When adding, renaming, or moving a maintained document inside an indexed directory, update the nearest required `README.md` index in the same change and verify the parent and child links;
5. Report conflicts, duplication, or uncertain facts instead of deleting or rewriting them.

## 4. Analyze change impact

Use the user request and Git diff to build an impact table. Check especially:

- whether public interfaces, commands, configuration, data models, or file formats affect API, design, usage, or migration documents;
- whether behavior, process, or architecture changes affect requirements, ADRs, testing strategy, or deployment guidance;
- whether release or delivery changes require a changelog, release notes, or operations manual update;
- whether project rules, directory structure, or tooling changes require updates to `AGENTS.md` and indexes.

Record related code, requirements, tests, and releases with relative paths in key topic documents. General rules may have no code relationship.

## 5. Plan and proceed

For medium- and high-impact work, report the following before editing. For a low-impact change, keep this as a short execution note; neither form is an approval gate:

~~~text
Scope: directories and files to inspect or change
Findings: missing, stale, duplicated, or conflicting documents
Plan: documents to create, update, split, archive, or index
Risks: facts not established by the repository and files that cannot be edited safely
Verification: evidence that will prove entry points, indexes, and relationships work
~~~

Use this impact table to decide how much process to show:

| Impact | Examples | Action |
| --- | --- | --- |
| Low | A typo, one topic update, or a mechanical link/date repair with known facts. | Inspect only the relevant entrypoint and target, make the authorized change, and run the relevant check. |
| Medium | A bounded interface, configuration, process, or multi-document update. | Give a concise impact summary, inspect only relevant safe diffs and sources, then update and verify. |
| High | Broad initialization/audit, conflicting sources of truth, sensitive-data handling, release decisions, or consequential moves/archives. | Inventory the paths and evidence, explain the proposed change, and pause only for material ambiguity or work beyond the user's authorized scope. |

An explicit request to change named documents or repair a stated issue authorizes that work and its required mechanical index/link updates. State the plan as an execution summary and proceed without a separate confirmation turn. Ask only when a fact, scope, or consequence is materially unclear, or an action would exceed the request. Do not ask again for a mechanical update already covered by the same authorization.

## 6. Resolve conflicts and preserve a single source of truth

When facts are duplicated or inconsistent, preserve the evidence and state:

- Intended behavior: the goal in requirements, an approved design, or the user's current request;
- Current behavior: what code, tests, deployment configuration, or existing documents actually say;
- Conflict location: the exact files and topics;
- Proposed source: which document should become authoritative, or which decision owner to consult if it remains unresolved.

Once the intended source is clear, consolidate repeated content into one topic document and link other locations or mark them `superseded`. Preserve historical information. Ask only if the user has not resolved a material conflict or the requested consolidation would remove information outside the authorized scope.

## 7. Run deterministic checks

Run `scripts/audit_docs.py --root <project-root>` after the planned updates. Use `--strict` for a merge or release gate; the `strict` governance level also treats warnings as failures. The helper applies the selected level to entrypoints, indexes, and metadata while continuing to check direct links, Markdown and image targets, Markdown anchors, duplicate IDs, configured stage names, existing and planned code relationships, supersession links, and common secret patterns. Link parsing ignores fenced code, inline code, and HTML comments; sensitive-value scanning continues to inspect fenced code. If it cannot run, perform equivalent checks manually and report the limitation.

## 8. Complete the governance check

Before completion, verify:

1. Root `AGENTS.md` exists; at `standard` or `strict`, the docs-root `README.md` also exists and links back to the entrypoint;
2. Every required topic index navigates upward and downward;
3. Indexed documents exist and important links are not broken;
4. Status, dates, and relationships match the current change;
5. Important constraints and decisions are not left only in conversation or code;
6. Output contains no secrets, tokens, passwords, or sensitive personal information;
7. The current stage gate is satisfied, or every unsatisfied item is explicitly listed.
