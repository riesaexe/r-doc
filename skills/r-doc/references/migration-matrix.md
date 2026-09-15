# Version migration matrix

## Scope

This matrix summarizes audit and workflow behavior changes that can affect an existing project. It is the compact upgrade view; the [repository CHANGELOG](https://github.com/riesaexe/r-doc/blob/main/CHANGELOG.md) remains the detailed release history.

Audit behavior changes can add findings without rewriting topic content. Pin a known-good tag in CI, run the preview and strict audit for the target version, and resolve findings before changing the pinned version.

## Version-by-version changes

| Version | Behavior change | Existing-project action | Upgrade risk |
| --- | --- | --- | --- |
| 0.2.0 | Introduced deterministic audit/repair helpers, stricter activation boundaries, and the first package validation gates. | Add the entrypoint and index structure; review the activation boundary before enabling implicit use. | Medium |
| 0.2.1 | Added YAML frontmatter parsing, broader secret detectors, and cross-platform CI. | Fix malformed frontmatter and review newly detected JWT, API-key, database-URL, and password findings. | Medium |
| 0.2.2 | Added Chinese password placeholders and nested-frontmatter dogfood coverage. | Replace real-looking Chinese examples with explicit placeholders or reviewed public examples. | Low |
| 0.2.3 | Made project configuration, bidirectional navigation, relationships, required types, and stage gates executable. | Configure the documentation root first, preview navigation repairs, add reverse links, then run strict audit. | High |
| 0.2.4 | Deduplicated repeated findings and documented migration from the 0.2.3 navigation rules. | Re-run audit and confirm that reduced output is deduplication, not a missing check. | Low |
| 0.2.5 | Added root Markdown scanning, image target validation, strict direct-child navigation, supersession closure, existing `related_code`, and invalid-stage errors. | Review root `README.md`/contribution/security files, image targets, parent-child index links, superseded documents, and CI stage names. | High |
| 0.2.6 | Added code/comment-aware link parsing, Markdown fragment checks, project exact allowlists, and `planned_code`. | Fix broken anchors; use `planned_code` for future files; review visible allowlist findings; confirm root exclusions. | High |
| 0.2.7 | Added GitHub-compatible ATX/Setext/CJK/custom-anchor checks, visible allowlist evidence, a complete configuration matrix, migration summary, and executable agent-evidence validation. | Re-run strict audit, review informational allowlist findings, and capture complete evidence before changing the pinned tag. | Medium |
| 0.2.8 | Extracted shared deterministic primitives into `scripts/rdoc/`, expanded Agent evaluation from five to eight scenarios, and preserved emoji code points in heading slugs. | Re-run package validation and anchor checks; if consuming the evaluation contract, add evidence for configuration, supersession, and anchor scenarios. | Low |
| 0.2.9 | Removed eager top-level `rdoc` re-exports and bound Agent evidence to the exact tested Skill version. | Update custom evidence producers with `skill_version`; direct submodule imports avoid package-wide initialization. | Low |
| 0.2.10 | Separated checked paths from read files, enforced successful ordered command evidence, split machine checks from review dimensions, and added shared-module regression tests. | Upgrade evidence to schema version 2; record `paths_checked`, use `required_command_sequence`, and provide a basis for each review dimension. | Medium |
| 0.2.11 | Added a validator-ready complete evidence example and made machine-dimension derivation rules explicit in `evals/cases.json`. | Replace copied evidence fragments with `evals/example-evidence.json` as a schema reference; keep custom case producers aligned with `machine_rules`. | Low |

## Safe upgrade sequence

1. Pin the current working tag and record its strict-audit result.
2. Copy the target Skill source into an isolated checkout; do not update the global install yet.
3. Run `python scripts/repair_docs.py --root <project-root>` and review the preview. Repair only structural links that are unambiguous.
4. Run `python scripts/audit_docs.py --root <project-root> --strict --json` and save the machine-readable result without sensitive content.
5. Resolve new errors and review warnings or informational allowlist findings with the project owner.
6. Update the pinned tag only after the target audit and the project's normal tests pass.

## Compatibility contract

The 0.2.x line may tighten deterministic audit coverage in patch releases. This is a governance-policy change, not an automatic rewrite of project prose. Consumers that require a stable gate should pin an exact tag and upgrade deliberately. The migration matrix is updated whenever a release changes audit findings, parser semantics, configuration behavior, or repair output.

[Back to the Skill entrypoint](../SKILL.md)
