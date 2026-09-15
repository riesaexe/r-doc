# Common pitfalls and guardrails

[简体中文版本](pitfalls.zh-CN.md)

## A file exists but is not reachable

Creating `docs/new-topic.md` is not enough. Add it to the nearest index and confirm that the index itself is reachable from `AGENTS.md` and `docs/README.md`. Use the safe repair preview for missing structural links, then run the strict audit.

## Repairing a conflict by overwriting facts

When code, tests, requirements, and documents disagree, preserve the evidence. Record intended behavior, current behavior, conflict location, and the decision owner. The repairer deliberately refuses to choose for you.

## Treating every code edit as a documentation project

Purely local refactors with no public behavior, data, configuration, architecture, or project-rule impact do not require the full governance loop. Use the activation gate in `SKILL.md` before spending context on documentation.

## Copying a template without changing its status

Templates contain example IDs, dates, statuses, and paths. Replace them with project values, keep the status honest, and add only documents that have a real owner or purpose. Run the metadata audit after copying.

## Leaving a generated document outside the index

Build output, coverage reports, generated API pages, and caches are not automatically maintained project knowledge. Exclude them or record the project convention explicitly; do not create indexes that pretend generated output is hand-maintained.

## Putting secrets in examples

Use fake, obviously invalid values or placeholders. Never paste credentials, private keys, personal tokens, production URLs with embedded secrets, or sensitive customer data into a document or example.

## Updating the installed copy first

The repository source under `skills/r-doc/` is the fact source. Update and verify it first, then synchronize a user-level installation. A globally installed copy is not a development workspace.

## Declaring success after a green structural check

The scripts prove structure and repeatability, not that every product statement is correct. The final report must still distinguish automated findings from semantic review, unresolved conflicts, and stage-gate decisions.
