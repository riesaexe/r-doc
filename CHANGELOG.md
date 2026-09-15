# Changelog

This file records user-visible changes to r-doc.

## [0.2.15] - 2026-09-15

- Upgraded the evidence schema to version 3 and required the trace to independently record `prompt`, `activation_decision`, `skill_selected`, `governance_report`, `final_response`, `diff_snapshot`, and human review; the aggregator derives and cross-validates these fields from the trace.
- Upgraded the trace schema to version 2 and rejected undeclared fields by event type; forbidden reads now lower `context_economy` in normal evaluation and fail under `--strict` and benchmark aggregation gates.
- Added trend, statistical, and strong-evidence sample thresholds for paired deltas, with 95% Student-t confidence intervals; added real Codex benchmark capture records and run instructions.
- Clarified the boundary between `condition` and Skill selection: the baseline still judges activation by scenario, and code-only scenarios select no r-doc Skill under either condition; failed real captures remain available for audit but are excluded from aggregation, and Windows CLI output is forced to UTF-8 for CJK and emoji traces.

## [0.2.14] - 2026-09-15

- Upgraded real Agent benchmark traces to structured JSONL with run-metadata binding, scenario lifecycle, and action events, and cross-validated path, read, command, and write evidence from the trace.
- Added paired `with-r-doc`/`baseline-no-r-doc` deltas keyed by `agent + model + run_id`, together with mean, median, standard deviation, and statistical readiness; profile summaries no longer mix conditions.
- Split context-economy read policy into required, allowed, and forbidden sets, reporting unnecessary, forbidden, and missing-required reads separately.
- Raised the default audit performance baseline to 10 iterations and recorded linearly interpolated p95, maximum values, and low-sample notices.

## [0.2.13] - 2026-09-15

- Added paired Chinese and English security-fix, practical-example, and common-pitfall reference documents for the GitHub public entrypoints; the Chinese README no longer routes users to English guides.
- Added Chinese backlinks for canonical English references and changed the Chinese Skill reference entrypoint to language-consistent document routes.
- Added public-document language-routing regression tests to prevent README links from drifting again.

## [0.2.12] - 2026-09-15

- Added the real Agent benchmark directory contract, run-evidence aggregator, and baseline notes without presenting example evidence as real results.
- Added bidirectional consistency checks for `machine_rules` identifiers, the code registry, and `cases.json` to prevent rule-name drift.
- Added an audit performance baseline tool for 100, 1,000, and 5,000 Markdown documents, together with the first local measurement record.

## [0.2.11] - 2026-09-15

- Added a complete Agent evidence example that can pass the evaluator directly, preventing documentation fragments from drifting away from the actual schema.
- Moved machine-dimension derivation rules into `machine_rules` in `evals/cases.json`; the evaluator now checks and reports them, making each dimension's inputs and pass conditions explicit.
- Added regression coverage for the complete evidence example so it cannot fall behind the implementation again.

## [0.2.10] - 2026-09-15

- Separated `paths_checked` from `files_read` in Agent evaluation evidence so checking a nonexistent path is not misreported as reading its contents.
- Changed required commands to an ordered success sequence and validated command names, integer exit codes, and declared order.
- Split scoring into evidence-derived machine checks and evidence-backed human review, reducing unsupported self-reported scores.
- Added regression tests for the shared `rdoc` modules; this version contains 59 regression tests.

## [0.2.9] - 2026-09-15

- Removed the top-level eager re-export from the `rdoc` package; audit, repair, and package-validation tools now import direct submodules, reducing package-initialization coupling.
- Added and enforced `skill_version` validation for Agent evaluation cases and evidence so cross-version results can be labeled and compared accurately.
- Added the 0.2.9 migration matrix and verification documentation; the regression suite grew to 51 tests.

## [0.2.8] - 2026-09-15

- Moved configuration loading, finding models, sensitive-value detection, Markdown target parsing, and heading-anchor generation into the shared `scripts/rdoc/` package for reuse by audit, repair, package validation, and Agent evaluation, reducing single-file responsibilities and import coupling.
- Expanded Agent evaluation from 5 to 8 scenarios, adding configuration-driven governance, superseded-document closure, and Markdown-anchor validation scenarios, with the evidence contract updated accordingly.
- Corrected emoji handling in heading slugs, preserving emoji code points and adding GitHub-compatible anchor regression tests.
- Kept all 50 regression tests passing and updated the verification, migration, and public documentation.

## [0.2.7] - 2026-09-15

- Expanded Markdown-anchor validation to GitHub-compatible ATX and Setext headings, CJK text, consecutive-space and punctuation boundaries, duplicate-heading suffixes, and explicit HTML `name`/`id` anchors, with matching regression tests.
- Kept `sensitive_allowlist` matches as informational findings and added a complete matrix for eight project-configuration fields, frontmatter ownership guidance for `planned_code`, and root-level `exclude` test evidence.
- Added a cross-version migration overview and executable Agent-evidence validator, documenting the upgrade strategy for patch releases that may add audit findings.
- Expanded temporary-project regression tests to 50 and passed the Skill-package, official Skill Creator, repair-preview, and strict-audit gates.

## [0.2.6] - 2026-09-15

- Made Markdown link parsing ignore fenced code, inline code, and HTML comments while continuing to scan sensitive values in fenced code; added Markdown fragment and anchor-existence validation.
- Added the `sensitive_allowlist` project configuration as a reviewed exact-example extension point for each detector, together with baseline detection for Google `AIza`-style API keys.
- Clarified root-level Markdown `exclude` behavior: `README.md` is included by default, configured exclusions also apply to root Markdown files, and `AGENTS.md` is always checked as an entrypoint.
- Added the `planned_code` metadata field for planned code paths that do not yet exist but must remain inside the project root, while preserving the existing-file requirement for `related_code`.
- Split temporary-project tests into focused audit-core, configuration/sensitive-value, and repairer modules while keeping 45 independently locatable regression scenarios.

## [0.2.5] - 2026-09-14

- Included directly maintained Markdown files in the project root in broken-link and sensitive-value audits, covering high-risk entrypoints such as README, contribution guides, and security notes; document metadata and index coverage remain limited to the configured `docs_root`.
- Made image links participate in target-existence checks without adding images or unused reference definitions to the documentation graph; nested indexes and their direct parent/child indexes must also be reachable in both directions.
- Added replacement-document relationships and body backlinks for `status: superseded`, existing-file validation for `related_code`, and immediate failure for an unconfigured `--stage`.
- Added an exact allowlist entry for the official public AWS example `AKIAIOSFODNN7EXAMPLE` while retaining sensitive-value scanning for other code-block content, avoiding a leakage blind spot under the label of “example code.”

## [0.2.4] - 2026-09-14

- Deduplicated repeated audit findings with the same path, finding type, message, and line number, reducing noise when symlinks or unreadable files are read by multiple check phases.
- Added migration guidance for existing 0.2.3 projects, covering bidirectional navigation, repair previews, and strict review steps.
- Added a deterministic coverage matrix for configuration, navigation, links, metadata relationships, and sensitive content to the verification documentation, together with evidence for 27 regression tests.

## [0.2.3] - 2026-09-14

- Made `.r-doc.yaml`, `docs/r-doc.yaml`, and `r-doc.yaml` drive the documentation root, exclusions, required document types, relationship requirements, and stage gates; duplicate or invalid configuration now becomes an audit error.
- Turned bidirectional entrypoint/index navigation, nested-index backlinks, and index coverage into deterministic audit rules; the repairer reuses the same configuration and fills navigation with one atomic update.
- Added support for reference-style Markdown links and parenthesized link targets, and checked resolved paths against the project-root boundary, including symlink-escape risks.
- Validated `related_docs`, `supersedes`, `review_after`, `related_code`, the title and first H1, creation/update ordering, and configured document-type relationships.
- Expanded temporary-project regression scenarios from 18 to 26, covering configuration, navigation, link parsing, metadata relationships, and stage gates.

## [0.2.2] - 2026-09-14

- Expanded the generic password-placeholder allowlist to include Chinese forms such as `你的密码`, `请输入你的密码`, `示例口令`, and `待填写`, and added regression coverage for real Chinese passwords.
- Added nested mappings and lists in frontmatter to the repository's own verification record as dogfood evidence for parser support.

## [0.2.1] - 2026-09-14

- Used PyYAML safe parsing for frontmatter, supporting nested mappings and lists; malformed YAML is reported explicitly instead of silently dropping fields.
- Removed the ineffective `strict` branch from audit functions, leaving warning thresholds to the command-line entrypoint.
- Expanded the sensitive-information baseline to JWTs, OpenAI API keys, credentialed database connection strings, and generic password assignments, while documenting coverage and known limitations.
- Added regression tests for frontmatter, parse failures, and new sensitive patterns.
- Expanded GitHub Actions to an Ubuntu/Windows and Python 3.10–3.13 matrix, with the PyYAML development dependency pinned.

## [0.2.0] - 2026-09-14

- Improved the `SKILL.md` discovery description and OpenAI UI short description with project-documentation governance, document-consistency, and change-tracking trigger terms.
- Added a skills.sh badge, quick-install section, and common-request entry table above the fold in the README.
- Made the English README the default global entrypoint while retaining `README.zh-CN.md` as the Chinese mirror with a language switch link.
- Translated the runtime `SKILL.md` into English while retaining `SKILL.zh-CN.md` as a Chinese explanatory mirror for global discovery and use.
- Rewrote the README's core principles, differentiators, and development-lifecycle governance guidance.
- Corrected GitHub and `npx skills` installation examples, clarifying the distinction between the repository source `riesaexe/r-doc` and the Skill name `r-doc`.
- Standardized runtime references and templates on English, and narrowed `SKILL.zh-CN.md` to a Chinese pointer for human maintainers to avoid a second drifting set of runtime rules.
- Added `audit_docs.py`, `validate_skill.py`, temporary-project unit tests, and GitHub Actions quality gates, reducing reliance on model self-discipline for verification.
- Added an `AGENTS.md` template, practical usage examples, and troubleshooting entrypoints covering core artifacts and the getting-started path.
- Tightened implicit activation boundaries so a purely code-only local change with no documentation impact does not start the full governance workflow.
- Removed personal machine paths from project documentation and replaced them with portable path expressions.
- Added a read-only-by-default safe-repair mode to `repair_docs.py`; only explicit `--apply` fills entrypoints, indexes, and missing links, while refusing to overwrite, delete, or resolve conflicts by guesswork.
- Added practical examples for initialization, interface changes, release audits, and topic directories, together with a centralized pitfalls and safeguards guide.

## [0.1.0] - 2026-09-14

- Established the initial r-doc Skill source copy.
- Added project-level `AGENTS.md` and documentation-governance conventions under `docs/`.
- Added lifecycle checklists, metadata rules, project-configuration guidance, and core templates.
- Completed the initial verification of the global installation copy.
