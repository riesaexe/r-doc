# Safe repair mode

[简体中文版本](repair.zh-CN.md)

## Purpose

`repair_docs.py` turns a small set of structural findings into a reviewable, repeatable repair plan. It is a guardrail, not a semantic decision-maker.

## Preview first

Run from the Skill source directory:

~~~bash
python scripts/repair_docs.py --root <project-root>
~~~

The default mode is read-only. It loads the same project configuration as the audit helper. At `standard` and `strict`, it may propose creating missing `AGENTS.md`, the configured documentation-root `README.md`, or nested `README.md` indexes, and may add their required navigation links. At `minimal`, it does not generate documentation indexes.

## Apply within the authorized scope

~~~bash
python scripts/repair_docs.py --root <project-root> --apply
~~~

`--apply` recomputes the same safe action class at invocation and writes only those structural repairs. When the user's request already authorizes the documentation repair, review the preview and apply it in the same task; the preview is a scope and safety check, not a separate approval round. If the preview exposes a semantic conflict or out-of-scope change, pause for that decision. If the repository changed between preview and apply, preview again. The guarded apply path refuses to overwrite an existing file, delete or move content, or continue when an update target changes during the operation. A second run should be idempotent and report no pending safe repairs.

## What it will not guess

The repairer does not resolve broken links, duplicate IDs, stale claims, document conflicts, missing metadata, relationship conflicts, or sensitive content. Resolve those from repository evidence and pause only if the intended fact or scope remains materially unclear. Invalid or duplicate project configuration also stops repair rather than being guessed. Run `audit_docs.py --strict` after any repair and report the remaining findings.

## Exit statuses

| Status | Meaning |
| --- | --- |
| `0` | No safe repair is pending, or the requested repairs were applied |
| `1` | Invalid root, write failure, or concurrent-change conflict |
| `2` | Safe repairs are pending in preview mode; no files were changed |
