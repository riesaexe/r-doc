# Deterministic verification and temporary-project QA

## Run the helper

From the skill source directory, run:

~~~bash
python scripts/audit_docs.py --root <project-root>
python scripts/audit_docs.py --root <project-root> --strict
~~~

Preview safe structural repairs before the audit:

~~~bash
python scripts/repair_docs.py --root <project-root>
python scripts/repair_docs.py --root <project-root> --apply
~~~

The preview is read-only. Apply mode is explicit and guarded; read [repair.md](repair.md) before using it.

The helper is read-only. It checks:

- root `AGENTS.md` and `docs/README.md`;
- `README.md` indexes for documentation subdirectories;
- relative Markdown links and missing targets;
- whether documents under `docs/` are reachable from an index;
- supported frontmatter fields, lifecycle status, duplicate IDs, and dates;
- common secret and token patterns.

Use normal mode during exploration. Use `--strict` before merge or release so warnings also fail the command.

## Validate the skill package

Run:

~~~bash
python scripts/validate_skill.py .
~~~

This checks the package entrypoint, frontmatter, resource links, UI metadata, icon paths, and Python syntax for bundled helpers. It does not replace the official `skill-creator` validator when that validator is available.

## Temporary-project scenarios

The bundled tests create isolated temporary projects and cover:

1. a valid root entrypoint and nested index;
2. a missing required entrypoint;
3. a broken relative link;
4. an unindexed document;
5. a suspicious secret pattern;
6. a duplicate document ID.
7. a non-mutating repair preview, idempotent apply, missing index link, and concurrent-change refusal.

Run them with:

~~~bash
python -m unittest discover -s tests -p 'test_*.py'
~~~

Report the command, exit status, and relevant finding list. A green package validator does not prove that a target project's documents are semantically correct; it proves that the deterministic structural checks passed.
