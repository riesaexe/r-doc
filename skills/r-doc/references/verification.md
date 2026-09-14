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
- `README.md` indexes for documentation subdirectories;
- relative, reference-style, and parenthesized Markdown links, missing targets, and resolved paths that escape the project root;
- whether documents under the configured documentation root are reachable from an index;
- supported frontmatter fields, lifecycle status, duplicate IDs, dates, titles, relationship IDs, and configured document-type requirements;
- project configuration, including duplicate files, invalid fields, stage gates, exclusions, and custom documentation roots;
- common secret and token patterns.

The helpers use PyYAML's safe `BaseLoader` for frontmatter mappings, nested mappings, and block lists. Malformed YAML or a non-mapping frontmatter block is reported as `frontmatter-parse`; it is not treated as an empty metadata object. PyYAML is pinned in the repository's `requirements-dev.txt` so local and CI behavior use the same parser.

## Sensitive-value baseline

The deterministic baseline is intentionally visible and finite. `audit_docs.py` and `validate_skill.py` currently look for:

| Pattern | Finding code | Coverage boundary |
| --- | --- | --- |
| PEM private-key markers | `private-key-marker` | Detects the marker, not every encoded key format. |
| AWS access keys | `aws-access-key` | Detects `AKIA`-style access-key IDs, not every AWS credential form. |
| GitHub tokens | `github-token` | Detects classic, fine-grained, and legacy `gh*` token prefixes. |
| Slack tokens | `slack-token` | Detects `xox*` token prefixes. |
| Compact JWTs | `jwt` | Requires three JWT-like base64url segments. |
| OpenAI API keys | `openai-api-key` | Detects `sk-` and `sk-proj-`-style keys of sufficient length. |
| Database URLs with credentials | `database-connection-string` | Covers common PostgreSQL, MySQL, MariaDB, MongoDB, Redis, and AMQP URL schemes when `user:password@host` is present. |
| Generic password assignments | `generic-password` | Detects `password`, `passwd`, or `pwd` assignments with a non-placeholder value of at least eight characters; the built-in placeholder baseline includes common English markers and Chinese forms such as `你的密码`, `请输入你的密码`, `示例口令`, and `待填写`. |

This is a deterministic baseline, not a complete secret scanner. Encoded, obfuscated, short, provider-specific, or placeholder values can evade it, and new patterns must be added with false-positive-aware tests. A passing audit never proves that a document contains no sensitive information.

Use normal mode during exploration. Use `--strict` before merge or release so warnings also fail the command.

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
4. an unindexed document and an excluded generated directory;
5. a suspicious secret pattern;
6. a duplicate document ID;
7. invalid and custom project configuration, stage gates, required types, and type relationships;
8. metadata title, date-order, and related-document checks;
9. a non-mutating repair preview, idempotent apply, missing index routes, and concurrent-change refusal.

Run them with:

~~~bash
python -m unittest discover -s tests -p 'test_*.py'
~~~

Report the command, exit status, and relevant finding list. A green package validator does not prove that a target project's documents are semantically correct; it proves that the deterministic structural checks passed.
