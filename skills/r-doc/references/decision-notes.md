# Decision notes

Decision notes preserve reasoning that is easy to lose in a commit message or final-state document. `docs/` remains the source for current facts and instructions; decision notes record why an important choice was made, which alternatives were considered, and what consequences follow.

## When to write one

Write a note when a change affects public behavior, an interface, a data or wire format, configuration, architecture, a cross-file contract, a dependency or deployment boundary, testing strategy, release/process rules, a non-obvious bug fix, or a simplification with a meaningful trade-off.

Do not write one for mechanical formatting, local CRUD, routine renames, or changes whose rationale is already fully captured nearby. One note should explain one decision; do not use notes as a second implementation log or a dump of every experiment.

## Location and configuration

The conventional root is `.agents/notes/`. It is optional: existing projects are not required to create it. If the directory exists, the audit expects a root `README.md` and scans decision-note Markdown below it. `README.md` files at the root or in lifecycle subdirectories are navigation files, not decision notes, so nested indexes do not create a frontmatter conflict. A project may route the layer explicitly:

~~~yaml
decision_notes:
  root: .agents/notes
~~~

The configured path must stay inside the project root. A configured but missing root is an error. The default root is discovered only when it already exists. Notes are not part of the ordinary `docs/` index-coverage graph, but every note is checked for Markdown links and sensitive values.

Use this path shape:

~~~text
.agents/notes/
├── README.md
├── proposed/<class>/<slug>.md
├── implemented/<class>/<slug>.md
├── rejected/<class>/<slug>.md
└── archived/<class>/<slug>.md
~~~

Supported classes are `feature`, `bug-fix`, `simplification`, `architecture`, `process`, and `testing`. The `status` frontmatter value must match the lifecycle directory. There is intentionally no mandatory global `INDEX.md`; find high-churn notes through path search, links from related documents, or a small local index when useful.

## Frontmatter and sections

Every note has this minimum frontmatter:

~~~yaml
id: DEC-YYYYMMDD-short-name
type: decision
status: proposed
title: Short decision title
created: 2026-09-19
updated: 2026-09-19
related_docs:
  - DOC-001
related_code:
  - path/to/existing/file.py
planned_code:
  - path/to/planned/file.py
~~~

`related_docs`, `related_code`, and `planned_code` are optional lists. `related_code` must point to an existing in-root file; `planned_code` may point to a not-yet-created in-root path. `supersedes` is an optional note or document ID used when a new record replaces an earlier one. When it names a `DEC-...` note, the validator requires that note to exist, requires a Markdown link to it, and rejects supersession cycles. External document IDs are shape-checked but resolved by the project's normal documentation relationships.

All notes require non-empty `## Problem` and `## Alternatives considered` sections. Lifecycle-specific sections are:

| Lifecycle | Required sections | Writing rule |
| --- | --- | --- |
| `proposed` | `Proposal`, `Acceptance criteria`, `Risks` | Describe the intended change and how it can be accepted or rejected. |
| `implemented` | `Decision`, `Consequences` | Write the decision and current behavior in the present tense. Include benefits and costs. |
| `rejected` | `Proposal`, `Rejection reason` | Preserve what was considered and why it was not accepted. |
| `archived` | The original note's applicable sections | Keep only if the record may still explain a future decision, audit, or reversal; include `archived: YYYY-MM-DD`. |

An implemented note is not a proposal with only its status changed. Replace proposal-era headings with the current decision and consequences. If only part changes, update the owning note and explain the changed boundary. If the decision reverses or materially changes, create a new note with `supersedes` and link the records; do not erase the old rationale.

## Maintenance workflow

1. Search active and implemented note paths before proposing a related decision.
2. Read related current documentation and inspect the code or tests establishing present behavior.
3. Create a `proposed` note only when the trigger boundary above is met.
4. On acceptance, move it to `implemented/<class>/`, set `status: implemented`, and rewrite the body to use `Decision` and `Consequences`.
5. When rejected, move it to `rejected/<class>/`, set `status: rejected`, and record the rejection reason.
6. When a record no longer deserves active retrieval, move it to `archived/<class>/` after considering its future value. Archive by decision value, not age or word count.
7. Update current `docs/` facts when behavior changes. The note complements those facts; it never substitutes for them.

The validator is intentionally mechanical. It checks routing, frontmatter, dates, titles, section presence, relationships, links, and sensitive content. It does not decide whether the trade-off is wise or whether the note is semantically complete; review those questions as part of normal change review.

## Supersession and archiving

A changed decision keeps its history through a new note. Put the new note in the appropriate lifecycle/class path, set `supersedes` to the prior decision ID, and link the prior note from the new note. The audit reports a missing `DEC-...` target, a missing link, a self-reference, or a cycle. Update the current `docs/` facts separately; the relation is about rationale, not implementation ownership.

Use the lifecycle helper when an existing note no longer deserves active retrieval:

~~~bash
python scripts/decision_notes.py archive .agents/notes/implemented/architecture/example.md
python scripts/decision_notes.py archive --apply .agents/notes/implemented/architecture/example.md
~~~

The first command is read-only and prints the planned destination. `--apply` updates `status`, `updated`, and `archived`, then moves the note to `archived/<class>/`. It refuses missing roots, mismatched lifecycle/status, malformed frontmatter, concurrent edits, and an existing destination. Before the move it rewrites inbound relative Markdown links that target the note and reports them as `updated_links`; it does not generate indexes or create an empty successor. The link rewrite is limited to references that resolve to the archived source, so unrelated links are unchanged.

## Review questions

- Can a future maintainer identify the problem and rejected alternatives without reading the whole history?
- Does current documentation describe what is true now, while this note explains why?
- Are costs and benefits of the implemented decision explicit?
- If an earlier choice changed, are old and new records linked and is the supersession boundary clear?
- Does the note avoid secrets, duplicated implementation details, universal word-count rules, and speculative alternatives?
