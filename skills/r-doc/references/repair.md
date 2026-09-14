# Safe repair mode

## Purpose

`repair_docs.py` turns a small set of structural findings into a reviewable, repeatable repair plan. It is a guardrail, not a semantic decision-maker.

## Preview first

Run from the Skill source directory:

~~~bash
python scripts/repair_docs.py --root <project-root>
~~~

The default mode is read-only. It may propose creating missing `AGENTS.md`, `docs/README.md`, or nested `README.md` indexes, and adding links for existing Markdown documents that are not listed by an index.

## Apply after confirmation

~~~bash
python scripts/repair_docs.py --root <project-root> --apply
~~~

`--apply` recomputes the same safe action class at invocation and writes only those structural repairs. If the repository changed between preview and apply, preview again. The guarded apply path refuses to overwrite an existing file, delete or move content, or continue when an update target changes during the operation. A second run should be idempotent and report no pending safe repairs.

## What it will not guess

The repairer does not resolve broken links, duplicate IDs, stale claims, document conflicts, missing metadata, or sensitive content. Those findings need evidence and a human-confirmed decision. Run `audit_docs.py --strict` after any repair and report the remaining findings.

## Exit statuses

| Status | Meaning |
| --- | --- |
| `0` | No safe repair is pending, or the requested repairs were applied |
| `1` | Invalid root, write failure, or concurrent-change conflict |
| `2` | Safe repairs are pending in preview mode; no files were changed |
