# Document metadata

## Recommended frontmatter

Topic documents should use YAML frontmatter when the format supports it:

~~~yaml
---
id: DOC-001
type: design
status: draft
title: Example technical design
created: 2026-09-14
updated: 2026-09-14
owner: team-name
review_after: 2026-10-01
related_code:
  - src/example.ts
related_docs:
  - DOC-002
supersedes: DOC-000
---
~~~

Required fields for topic documents:

- `id`: a stable, unique document identifier within the project;
- `type`: a document type such as `requirements`, `design`, `adr`, `api`, `testing`, or `release`;
- `status`: one of the lifecycle states below;
- `title`: consistent with the document heading;
- `created` and `updated`: ISO 8601 dates or timezone-aware timestamps.

Conditional fields:

- `owner`: for documents that need ongoing maintenance or review;
- `review_after`: for documents with a review cadence;
- `related_code`: relative paths for existing files affected by code, configuration, or data-model changes;
- `related_docs`: documents whose facts this document depends on;
- `supersedes`: the old document replaced by this one.

The deterministic audit validates the relationships that can be checked without interpreting project prose:

- `created`, `updated`, and `review_after` must be valid ISO dates or timestamps; `updated` cannot precede `created`, and a past `review_after` is a warning;
- `title` must match the first H1 when both are present;
- `related_docs` must be a list of existing document IDs, and `supersedes` must name an existing document ID;
- `related_code` must be a list of existing files whose canonical paths remain inside the project root;
- a document with `status: superseded` must have a distinct successor document whose `supersedes` field names its ID, and must link to that successor in its Markdown body;
- a project's `relationships.require_for` configuration can require relationships between document types.

These checks validate references and structure, not whether the linked documents are semantically correct.

Root `AGENTS.md` and index `README.md` files are navigation entry points. They may use lighter metadata, but must have a clear title, scope, update information, or equivalent navigation evidence.

## Status semantics

~~~text
draft      Being written; not a final rule
proposed   A formed proposal awaiting review or approval
active     A current project fact or rule
superseded Replaced by a newer document; a successor must declare `supersedes` for this ID, and this document must link to that successor
archived   Historical material; excluded from current rule decisions by default
~~~

Do not use `active` to hide an unapproved draft. Do not turn implemented behavior that differs from the intended design into an `active` rule without recording the conflict.

## Document types

Types are not a closed enum. Keep the meaning of these common types stable:

~~~text
requirements  Goals, scope, and acceptance criteria
design        Technical approach and boundaries
adr           Architecture or major decision
api           Interfaces, commands, data formats, and compatibility
testing       Test strategy, plans, reports, and evidence
release       Release, change, and upgrade notes
operations    Deployment, operations, migration, rollback, and troubleshooting
guide         Instructions for maintainers or users
policy        Project rules and constraints
~~~
