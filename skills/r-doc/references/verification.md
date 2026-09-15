# Deterministic verification and temporary-project QA

## Run the helper

From the skill source directory, run:

~~~bash
python -m pip install -r scripts/requirements.txt
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

- root `AGENTS.md`, the configured documentation root, and their required bidirectional navigation;
- directly maintained Markdown files in the project root, such as `README.md`, `CONTRIBUTING.md`, and `SECURITY.md`, for links and sensitive values; `README.md` is included by default, and `exclude` applies to these root files as well; metadata and index coverage remain scoped to the configured documentation root;
- `README.md` indexes for documentation subdirectories;
- relative, reference-style, parenthesized, and image Markdown links, missing targets, missing Markdown anchors, and resolved paths that escape the project root; fenced code blocks, inline code spans, and HTML comments are excluded from link parsing; unused reference definitions are checked for target existence but do not create navigation edges;
- GitHub-compatible anchor targets from ATX and Setext headings, duplicate heading suffixes, Unicode/CJK text, preserved emoji code points, punctuation and consecutive-space cases, plus explicit `<a name="...">` and `<a id="...">` anchors; renderer-specific anchor rules outside this contract are not inferred;
- whether documents under the configured documentation root are reachable from an index;
- supported frontmatter fields, lifecycle status, duplicate IDs, dates, titles, relationship IDs, existing `related_code` files, non-existent-but-in-root `planned_code` paths, supersession successors and successor links, and configured document-type requirements;
- project configuration, including duplicate files, invalid fields, configured stage names, stage gates, exclusions, and custom documentation roots;
- common secret and token patterns.

The helpers use PyYAML's safe `BaseLoader` for frontmatter mappings, nested mappings, and block lists. Malformed YAML or a non-mapping frontmatter block is reported as `frontmatter-parse`; it is not treated as an empty metadata object. PyYAML is pinned in the repository's `requirements-dev.txt` so local and CI behavior use the same parser.

Shared deterministic primitives live in `scripts/rdoc/`: configuration loading, finding models, sensitive-value detectors, Markdown target parsing, and anchor generation. The command wrappers remain thin entrypoints so audit, repair, package validation, and Agent-evidence evaluation use the same implementation.

## Sensitive-value baseline

The deterministic baseline is intentionally visible and finite. `audit_docs.py` and `validate_skill.py` currently look for:

| Pattern | Finding code | Coverage boundary |
| --- | --- | --- |
| PEM private-key markers | `private-key-marker` | Detects the marker, not every encoded key format. |
| AWS access keys | `aws-access-key` | Detects `AKIA`-style access-key IDs, not every AWS credential form. |
| GitHub tokens | `github-token` | Detects classic, fine-grained, and legacy `gh*` token prefixes. |
| Google API keys | `google-api-key` | Detects `AIza`-style API keys of sufficient length. |
| Slack tokens | `slack-token` | Detects `xox*` token prefixes. |
| Compact JWTs | `jwt` | Requires three JWT-like base64url segments. |
| OpenAI API keys | `openai-api-key` | Detects `sk-` and `sk-proj-`-style keys of sufficient length. |
| Database URLs with credentials | `database-connection-string` | Covers common PostgreSQL, MySQL, MariaDB, MongoDB, Redis, and AMQP URL schemes when `user:password@host` is present. |
| Generic password assignments | `generic-password` | Detects `password`, `passwd`, or `pwd` assignments with a non-placeholder value of at least eight characters; the built-in placeholder baseline includes common English markers and Chinese forms such as `你的密码`, `请输入你的密码`, `示例口令`, and `待填写`. |

This is a deterministic baseline, not a complete secret scanner. Link parsing excludes fenced code, but sensitive-value scanning still scans fenced code because real credentials can be copied into configuration examples. The exact public AWS documentation sample `AKIAIOS7FODNN7EXAMPLE` is built in. Projects may add exact, provider-documented examples under `sensitive_allowlist` in `.r-doc.yaml`; the key must be a supported detector code and the value must be an exact string, not a regular expression. Each match is retained as an informational `allowlisted-sensitive-example` finding so the exception remains visible in audit evidence. Treat this configuration as a reviewed security exception and never use it for a real credential. Encoded, obfuscated, short, provider-specific, or placeholder values can evade the baseline, and new patterns must be added with false-positive-aware tests. A passing audit never proves that a document contains no sensitive information.

Use normal mode during exploration. Use `--strict` before merge or release so warnings also fail the command.

## Migrating an existing project

The bidirectional navigation rule is intentional. After adopting the 0.2.3 governance checks, an existing project may newly report `missing-navigation-link` when `docs/README.md` does not link back to `AGENTS.md`, or when a nested `README.md` does not link to its parent index. This is an adaptation requirement, not a content rewrite requirement. For the complete behavior-change history from 0.2.0 through the current release, read [migration-matrix.md](migration-matrix.md).

For a safe migration:

1. Run `repair_docs.py --root <project-root>` and review the preview;
2. Confirm that the proposed links point to the intended entrypoint and parent indexes;
3. Run `repair_docs.py --root <project-root> --apply` only after review;
4. Run `audit_docs.py --root <project-root> --strict` and resolve any remaining semantic findings manually.

The repairer adds navigation and index links without rewriting topic content. Projects with a custom `docs_root` should configure it before previewing the migration.

## Coverage map

The deterministic checks currently cover:

| Area | Executed checks |
| --- | --- |
| Project configuration | Lookup precedence, duplicate files, unknown fields, path safety, exclusions, required document types, relationship requirements, configured stage names, and stage gates. |
| Navigation and coverage | Root entrypoint/index bidirectionality, strict parent-to-direct-child index links, index coverage, missing indexes, safe canonical paths, and root Markdown exclusion behavior. Images and unused reference definitions are validation targets, not navigation edges. |
| Markdown links | Inline, reference-style, parenthesized, image, broken, broken-anchor, unused-definition, and project-root-escaping targets, with code/comment masking for link syntax. |
| Metadata relationships | IDs, title/H1 consistency, ISO dates and ordering, review dates, `related_docs`, `supersedes`, existing `related_code` files, in-root `planned_code` paths, and superseded-document successor links. |
| Sensitive content | The finite token, credential, JWT, Google API key, database URL, password baseline, built-in AWS sample exception, project-configured exact examples, and visible allowlist evidence documented below. |

## Empirical and scale benchmarks

The Agent-evaluation schema is not a benchmark result. Store real runs with an actual trace under the repository's `benchmarks/<profile>/run-<number>/` layout and use `aggregate_benchmarks.py` to regenerate `result.json` and `summary.json`; keep `with-r-doc` and `baseline-no-r-doc` conditions separate and capture at least three runs per condition. A missing run remains `pending` rather than becoming a zero or passing score.

Use `benchmark_audit.py` for the separate deterministic scale baseline:

~~~bash
python scripts/benchmark_audit.py --sizes 100,1000,5000 --iterations 3 --warmup 0 --output ../../benchmarks/performance-baseline.json
~~~

The recorded median and p95 wall-clock values are machine-specific trend data. They are useful for discovering scale risks, but are not a universal CI threshold.

## Validate the skill package

Run:

~~~bash
python scripts/validate_skill.py .
~~~

This checks the package entrypoint, frontmatter, resource links, UI metadata, icon paths, and Python syntax for bundled helpers. It does not replace the official `skill-creator` validator when that validator is available.

## Temporary-project scenarios

The bundled tests create isolated temporary projects and cover:

1. a valid root entrypoint and nested index with bidirectional navigation;
2. a missing required entrypoint;
3. broken, reference-style, parenthesized, and out-of-root links;
4. a broken image, an unused reference definition, an unindexed document, and an excluded generated directory;
5. root-level Markdown link and sensitive-content checks, including root exclusions and default README scanning;
6. links inside fenced code, inline code, and HTML comments, plus valid and missing Markdown anchors;
7. suspicious secret patterns, the allowlisted AWS documentation example, a project-specific exact allowlist, and visible informational evidence for allowlisted matches;
8. a duplicate document ID;
9. invalid and custom project configuration, invalid stage names, stage gates, required types, and type relationships;
10. metadata title, date-order, related-document, existing-code-target, planned-code, and supersession-successor checks;
11. GitHub-compatible ATX/Setext/CJK/emoji/duplicate/custom-anchor fragment checks;
12. configuration-driven, supersession-closure, and Agent-evidence evaluation scenarios;
13. a non-mutating repair preview, idempotent apply, strict direct-child index routes, missing index routes, and concurrent-change refusal.

Run them with:

~~~bash
python -m unittest discover -s tests -p 'test_*.py'
~~~

Report the command, exit status, and relevant finding list. A green package validator does not prove that a target project's documents are semantically correct; it proves that the deterministic structural checks passed.
