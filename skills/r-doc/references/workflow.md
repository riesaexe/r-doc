# r-doc workflow

## 1. Confirm scope

Prefer `git rev-parse --show-toplevel` to identify the project root. If the current directory is not a Git project, use the project root explicitly named by the user. Do not mistake a personal directory or workspace parent for the project root.

After confirming scope, read the existing root `AGENTS.md`, `docs/README.md`, relevant topic indexes, and project-level `.r-doc.yaml`. Do not read the entire repository just to understand it; use indexes to select the minimum document set.

## 2. Inventory documentation

Inventory the non-code material maintained by the project team: plans, requirements, designs, decisions, interfaces, tests, releases, deployments, rules, guides, processes, and records. Exclude by default:

- `.git/`, dependency, vendor, cache, and temporary directories;
- build output, logs, coverage output, and fully generated files that are not hand-maintained;
- source code, test code, and scripts themselves.

Register unknown formats before editing them. Binary documents may be checked for existence, status, index coverage, and relationships, but edit them only with an appropriate document tool and user confirmation.

The deterministic audit also scans directly maintained Markdown files in the project root, including `README.md`, `CONTRIBUTING.md`, and `SECURITY.md`, for broken links and sensitive values. `README.md` is included by default, and `.r-doc.yaml` `exclude` applies to root Markdown as well. Metadata, index coverage, and lifecycle relationships remain scoped to Markdown documents under the configured `docs_root`; generated or excluded paths are not scanned. `AGENTS.md` is the mandatory entrypoint and is always checked.

## 3. Initialize or repair entry points

When entry points are missing, propose a minimal initialization plan, normally creating only `AGENTS.md` and `docs/README.md`. Create topic directories and documents only when the real project needs them. `AGENTS.md` should contain project navigation, common commands, mandatory rules, prohibitions, context-loading order, task or module routes, and a link to `docs/README.md`.

When entry points already exist:

1. Preserve existing facts, constraints, and historical links;
2. Fill missing navigation and indexes;
3. Keep reverse links when moving detail into `docs/`;
4. Report conflicts, duplication, or uncertain facts instead of deleting or rewriting them.

## 4. Analyze change impact

Use the user request and Git diff to build an impact table. Check especially:

- whether public interfaces, commands, configuration, data models, or file formats affect API, design, usage, or migration documents;
- whether behavior, process, or architecture changes affect requirements, ADRs, testing strategy, or deployment guidance;
- whether release or delivery changes require a changelog, release notes, or operations manual update;
- whether project rules, directory structure, or tooling changes require updates to `AGENTS.md` and indexes.

Record related code, requirements, tests, and releases with relative paths in key topic documents. General rules may have no code relationship.

## 5. Plan and confirm

Before writing, report:

~~~text
Scope: directories and files to inspect or change
Findings: missing, stale, duplicated, or conflicting documents
Plan: documents to create, update, split, archive, or index
Risks: facts not established by the repository and files that cannot be edited safely
Verification: evidence that will prove entry points, indexes, and relationships work
~~~

Write only after the user confirms the plan. Do not ask again for mechanical index, link, date, or status updates that were already approved within the same task. Pause again when the scope, facts, or risk changes.

## 6. Resolve conflicts and preserve a single source of truth

When facts are duplicated or inconsistent, preserve the evidence and state:

- Intended behavior: the goal in requirements, an approved design, or the user's current request;
- Current behavior: what code, tests, deployment configuration, or existing documents actually say;
- Conflict location: the exact files and topics;
- Proposed source: which document should become authoritative and who must confirm it.

After confirmation, consolidate repeated content into one topic document. Link from other locations or mark them `superseded`; do not delete historical information without confirmation.

## 7. Run deterministic checks

Run `scripts/audit_docs.py --root <project-root>` after the planned updates. Use `--strict` for a merge or release gate. The helper checks entry points, nested indexes, direct parent/child navigation, Markdown and image links, Markdown anchors, index coverage, document metadata, duplicate IDs, configured stage names, existing and planned code relationships, supersession links, and common secret patterns. Link parsing ignores fenced code, inline code, and HTML comments; sensitive-value scanning continues to inspect fenced code. If it cannot run, perform equivalent checks manually and report the limitation.

## 8. Complete the governance check

Before completion, verify:

1. Root `AGENTS.md` and `docs/README.md` exist and are reachable from one another;
2. Every topic index navigates upward and downward;
3. Indexed documents exist and important links are not broken;
4. Status, dates, and relationships match the current change;
5. Important constraints and decisions are not left only in conversation or code;
6. Output contains no secrets, tokens, passwords, or sensitive personal information;
7. The current stage gate is satisfied, or every unsatisfied item is explicitly listed.
