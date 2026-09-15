# Practical examples

[简体中文版本](examples.zh-CN.md)

## Example 1: Initialize an existing repository

Suppose a repository contains source code and a user-facing README but no project documentation entrypoint:

~~~text
storefront/
├── README.md
├── src/
└── tests/
~~~

Ask:

~~~text
$r-doc Inspect this repository and establish the documentation entrypoints. Preserve existing facts, show the safe repair plan first, and do not modify business code.
~~~

Preview:

~~~text
r-doc repair: PLAN
CREATE AGENTS.md - create missing project entrypoint
CREATE docs/README.md - create missing documentation index
~~~

After confirmation, run the same command with `--apply`, then complete project-specific commands and rules in `AGENTS.md`. The generated files are navigation scaffolding, not a claim that the repository knowledge is complete.

## Example 2: Trace an API change

If `POST /users` gains a required `role` field, ask for an impact pass:

~~~text
$r-doc The public POST /users request now requires role. Trace the documentation impact, update the API and testing documents, and report any conflict between the implementation, tests, and current docs.
~~~

The expected report identifies the affected API contract, request examples, validation behavior, test scenarios, migration or compatibility notes, and release documentation. If the code and design disagree, r-doc reports both facts instead of silently choosing one.

## Example 3: Audit before release

Run the deterministic checks from the project root:

~~~bash
python skills/r-doc/scripts/repair_docs.py --root .
python skills/r-doc/scripts/audit_docs.py --root . --strict
~~~

The first command previews only safe structural repairs. The second checks the resulting entrypoints, nested indexes, links, coverage, metadata, duplicate IDs, and common sensitive-value patterns. A passing structural audit does not prove that product claims are true; the release report must still record semantic review and unresolved decisions.

## Example 4: A focused topic directory

For a project with separate API documents, use one index as the boundary:

~~~text
docs/
├── README.md
└── api/
    ├── README.md
    ├── users.md
    └── billing.md
~~~

`docs/api/README.md` explains the API-document scope, links the parent index, lists `users.md` and `billing.md`, and states the recommended reading order. A new `payments.md` should be added to that index in the same change; the repairer can add the missing link without rewriting the API content.
