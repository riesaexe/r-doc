# Lifecycle checklists

Choose the checks that match the current stage. Do not create empty documents for unrelated stages.

## Planning

- Goals, scope, non-goals, and constraints are clear;
- Acceptance criteria or observable outcomes are explicit;
- Background, users, dependencies, and risks have sources;
- The root `AGENTS.md` and `docs/README.md` lead to the planning material;
- The impact on later design, testing, and release documentation is identified.

## Design

- Technical approach, boundaries, interfaces, data, and failure paths are documented;
- Important or irreversible decisions have an ADR with context, options, decision, and consequences;
- Design documents link to requirements, code entry points, and the test strategy;
- When a design changes, the old decision is marked superseded or archived instead of leaving two active facts.

## Implementation

- The documentation impact of code and configuration changes is assessed;
- Public behavior, interfaces, configuration, data formats, commands, and migration steps are synchronized;
- New non-obvious constraints, pitfalls, and operating steps are recorded;
- The change does not put sensitive values in documentation or examples.

## Review or merge

- Requirements, design, code, tests, and documentation describe the same behavior consistently;
- Affected documents are reachable through indexes;
- Links, status, dates, and relationships are valid;
- Remaining issues are explicitly marked blocking or non-blocking;
- “The code works” is not used as a substitute for documentation completion.

## Release

- Changelog and release notes accurately describe user-visible changes;
- Deployment, migration, rollback, configuration, and operations guidance is updated;
- Breaking changes, compatibility, and upgrade steps are explicit;
- Release documentation links to the related requirement, design, test, or decision.

## Maintenance and archival

- Document owners, status, and last-updated dates are still valid;
- Invalid content is marked `superseded` or `archived` and points to its replacement;
- An index preserves historical traceability before removing an obsolete entry;
- Archived content cannot be mistaken for a current rule by maintainers.

## Default gate

Use audit mode by default: do not declare the current stage complete while critical documentation issues remain unresolved. A project may raise a stage to `release` or `blocking` in `.r-doc.yaml`, but configuration cannot disable sensitive-content protection, conflict reporting, or evidence requirements.
