from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

STATUS_VALUES = {"draft", "proposed", "active", "superseded", "archived"}
from rdoc.config import ProjectConfig, _string_list, canonical_path, load_project_config, path_is_excluded, relative
from rdoc.io import add, read_text
from rdoc.markdown import (
    FrontmatterParseError,
    _anchor_slug,
    markdown_anchors,
    navigation_targets,
    parse_frontmatter,
    target_reference,
    validation_targets,
)
from rdoc.models import Finding, FindingList
from rdoc.notes import check_decision_notes, decision_note_files
from rdoc.security import SECRET_PATTERNS, is_safe_example


def markdown_files(directory: Path, root: Path, config: ProjectConfig) -> list[Path]:
    if not directory.is_dir():
        return []
    paths: list[Path] = []
    for path in directory.rglob("*.md"):
        if path_is_excluded(root, path, config):
            continue
        paths.append(path)
    return sorted(paths)


def root_markdown_files(root: Path, config: ProjectConfig) -> list[Path]:
    return sorted(
        path
        for path in root.glob("*.md")
        if path.is_file() and path.name != "AGENTS.md" and not path_is_excluded(root, path, config)
    )


def check_links(root: Path, files: list[Path], findings: list[Finding]) -> dict[Path, set[Path]]:
    outgoing: dict[Path, set[Path]] = {}
    for path in files:
        text = read_text(path, root, findings)
        targets: set[Path] = set()
        for target in validation_targets(text):
            reference = target_reference(path, target.raw_target, root)
            if reference is None or reference.path is None:
                continue
            resolved = reference.path
            if resolved.is_dir():
                resolved = resolved / "README.md"
            canonical = canonical_path(root, resolved)
            if canonical is None:
                add(findings, "error", "link-outside-root", root, path, f"link leaves the project root: {target.raw_target}", target.line)
                continue
            if not canonical.exists():
                add(findings, "error", "broken-link", root, path, f"target does not exist: {target.raw_target}", target.line)
            elif reference.fragment and canonical.suffix.lower() == ".md":
                anchors = markdown_anchors(canonical, root, findings)
                normalized_fragment = _anchor_slug(reference.fragment)
                normalized_anchors = {anchor.lower() for anchor in anchors}
                if reference.fragment.lower() not in normalized_anchors and normalized_fragment.lower() not in normalized_anchors:
                    add(findings, "error", "broken-anchor", root, path, f"anchor does not exist: {target.raw_target}", target.line)
            if not target.is_image and not target.is_definition and not reference.fragment_only:
                targets.add(canonical)
        outgoing[path] = targets
    return outgoing


def check_navigation(root: Path, docs: Path, files: list[Path], outgoing: dict[Path, set[Path]], agents: Path, findings: list[Finding]) -> None:
    routes: list[tuple[Path, Path]] = []
    docs_index = docs / "README.md"
    if agents.is_file():
        routes.append((agents, docs_index))
    if docs_index.is_file():
        routes.append((docs_index, agents))
    for index in files:
        if index.name == "README.md" and index != docs_index:
            parent_index = index.parent.parent / "README.md"
            routes.append((index, parent_index))
            if parent_index.is_file():
                routes.append((parent_index, index))
    for source, target in routes:
        source_key = canonical_path(root, source)
        target_key = canonical_path(root, target)
        if source_key is not None and (target_key is None or target_key not in outgoing.get(source, set())):
            add(findings, "error", "missing-navigation-link", root, source, f"navigation link is required: {relative(root, target)}")


def check_indexes(root: Path, docs: Path, files: list[Path], outgoing: dict[Path, set[Path]], findings: list[Finding], config: ProjectConfig, agents: Path) -> None:
    if not docs.is_dir():
        return
    for directory in sorted(path for path in docs.rglob("*") if path.is_dir()):
        if path_is_excluded(root, directory, config):
            continue
        contains_markdown = any(path in files for path in directory.rglob("*.md"))
        if contains_markdown and not (directory / "README.md").is_file():
            add(findings, "error", "missing-nested-index", root, directory, "directory contains Markdown documents but no README.md")

    docs_index = canonical_path(root, docs / "README.md")
    incoming: dict[Path, int] = {}
    for path in files:
        canonical = canonical_path(root, path)
        if canonical is not None and canonical != docs_index:
            incoming[canonical] = 0
    index_files = [path for path in files if path.name == "README.md"]
    index_files.extend(path for path in [root / "AGENTS.md"] if path.exists())
    for index in index_files:
        for target in outgoing.get(index, set()):
            if target in incoming:
                incoming[target] += 1
    for path, count in incoming.items():
        if count == 0:
            add(findings, "error", "unindexed-document", root, path, "document is not reachable from AGENTS.md or an index README.md")
    check_navigation(root, docs, files, outgoing, agents, findings)


def parse_iso_date(value: object) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        if "T" in normalized or "t" in normalized:
            return datetime.fromisoformat(normalized).date()
        return date.fromisoformat(normalized)
    except ValueError:
        return None


def first_heading(text: str) -> str | None:
    for line in text.splitlines():
        match = re.match(r"^\s*#\s+(.+?)\s*#*\s*$", line)
        if match:
            return match.group(1).strip()
    return None


def check_metadata(
    root: Path,
    docs: Path,
    files: list[Path],
    outgoing: dict[Path, set[Path]],
    findings: list[Finding],
    config: ProjectConfig,
) -> tuple[dict[Path, dict[str, object]], dict[str, Path]]:
    records: dict[Path, dict[str, object]] = {}
    seen_ids: dict[str, Path] = {}
    relation_values: dict[Path, dict[str, object]] = {}
    for path in files:
        if path.name == "README.md":
            continue
        text = read_text(path, root, findings)
        try:
            values, _ = parse_frontmatter(text)
        except FrontmatterParseError as error:
            add(findings, "error", "frontmatter-parse", root, path, str(error))
            continue
        if not values:
            add(findings, "warning", "metadata-missing", root, path, "topic document has no frontmatter")
            continue
        records[path] = values
        relation_values[path] = values
        for key in ("id", "type", "status", "title", "created", "updated"):
            value = values.get(key)
            if not isinstance(value, str) or not value.strip():
                add(findings, "error", "metadata-field", root, path, f"missing frontmatter field: {key}")
        status = values.get("status")
        if status and (not isinstance(status, str) or status not in STATUS_VALUES):
            add(findings, "error", "metadata-status", root, path, f"unsupported status: {status}")

        parsed_dates: dict[str, date] = {}
        for key in ("created", "updated", "review_after"):
            value = values.get(key, "")
            if value:
                parsed = parse_iso_date(value)
                if parsed is None:
                    add(findings, "error", "metadata-date", root, path, f"invalid {key} date: {value}")
                else:
                    parsed_dates[key] = parsed
        if "created" in parsed_dates and "updated" in parsed_dates and parsed_dates["updated"] < parsed_dates["created"]:
            add(findings, "error", "metadata-date-order", root, path, "updated date is earlier than created date")
        if "review_after" in parsed_dates and parsed_dates["review_after"] < date.today():
            add(findings, "warning", "review-overdue", root, path, f"review_after date has passed: {values['review_after']}")

        title = values.get("title")
        heading = first_heading(text)
        if isinstance(title, str) and heading and title.strip() != heading:
            add(findings, "error", "metadata-title", root, path, f"frontmatter title does not match the first H1: {title!r} != {heading!r}")

        identifier = values.get("id")
        if isinstance(identifier, str) and identifier.strip():
            identifier = identifier.strip()
            if identifier in seen_ids:
                add(findings, "error", "duplicate-id", root, path, f"ID also used by {relative(root, seen_ids[identifier])}: {identifier}")
            else:
                seen_ids[identifier] = path

        for key in ("related_docs", "related_code", "planned_code"):
            if key in values:
                value = values[key]
                if _string_list(value) is None:
                    add(findings, "error", "metadata-relationship", root, path, f"{key} must be a list of non-empty strings")
        supersedes = values.get("supersedes")
        if supersedes is not None and (not isinstance(supersedes, str) or not supersedes.strip()):
            add(findings, "error", "metadata-relationship", root, path, "supersedes must be a non-empty document ID")
        related_code = values.get("related_code")
        if isinstance(related_code, list):
            for code_path in related_code:
                if not isinstance(code_path, str):
                    continue
                canonical = canonical_path(root, root / code_path)
                if canonical is None:
                    add(findings, "error", "related-code-outside-root", root, path, f"related_code leaves the project root: {code_path}")
                elif not canonical.is_file():
                    add(findings, "error", "related-code-missing", root, path, f"related_code target is not an existing file: {code_path}")
        planned_code = values.get("planned_code")
        if isinstance(planned_code, list):
            for code_path in planned_code:
                if not isinstance(code_path, str):
                    continue
                if canonical_path(root, root / code_path) is None:
                    add(findings, "error", "planned-code-outside-root", root, path, f"planned_code leaves the project root: {code_path}")

    document_types: dict[str, set[str]] = {}
    for values in records.values():
        document_type = values.get("type")
        identifier = values.get("id")
        if isinstance(document_type, str) and isinstance(identifier, str) and identifier.strip():
            document_types.setdefault(document_type, set()).add(identifier.strip())

    successor_paths: dict[str, set[Path]] = {}
    for successor_path, values in relation_values.items():
        supersedes = values.get("supersedes")
        canonical_successor = canonical_path(root, successor_path)
        if isinstance(supersedes, str) and supersedes in seen_ids and canonical_successor is not None:
            successor_paths.setdefault(supersedes, set()).add(canonical_successor)

    for path, values in relation_values.items():
        related_docs = values.get("related_docs")
        if isinstance(related_docs, list):
            for identifier in related_docs:
                if isinstance(identifier, str) and identifier not in seen_ids:
                    add(findings, "error", "related-doc-missing", root, path, f"related document ID does not exist: {identifier}")
        supersedes = values.get("supersedes")
        if isinstance(supersedes, str) and supersedes not in seen_ids:
            add(findings, "error", "supersedes-missing", root, path, f"superseded document ID does not exist: {supersedes}")

        identifier = values.get("id")
        if values.get("status") == "superseded" and isinstance(identifier, str) and identifier.strip():
            replacements = successor_paths.get(identifier.strip(), set())
            current_path = canonical_path(root, path)
            replacements = {successor_path for successor_path in replacements if successor_path != current_path}
            if not replacements:
                add(findings, "error", "superseded-successor-missing", root, path, "superseded document has no successor that declares supersedes")
            elif not replacements.intersection(outgoing.get(path, set())):
                add(findings, "error", "superseded-successor-unlinked", root, path, "superseded document does not link to its successor")

        document_type = values.get("type")
        requirements = config.relationships or {}
        required_types = requirements.get(document_type, ()) if isinstance(document_type, str) else ()
        related_ids = set(related_docs) if isinstance(related_docs, list) else set()
        for target_type in required_types:
            if not related_ids.intersection(document_types.get(target_type, set())):
                add(findings, "error", "relationship-required", root, path, f"{document_type} documents must relate to at least one {target_type} document")

    existing_types = set(document_types)
    for required_type in config.required_document_types:
        if required_type not in existing_types:
            add(findings, "error", "required-document-type", root, docs, f"required document type is missing: {required_type}")
    return records, seen_ids


def check_sensitive_content(
    root: Path,
    files: list[Path],
    findings: list[Finding],
    config: ProjectConfig | None = None,
) -> None:
    for path in files:
        text = read_text(path, root, findings)
        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern, code in SECRET_PATTERNS:
                matches = list(pattern.finditer(line))
                allowlist = config.sensitive_allowlist if config else None
                if any(is_safe_example(code, match.group(0), allowlist) for match in matches):
                    add(
                        findings,
                        "info",
                        "allowlisted-sensitive-example",
                        root,
                        path,
                        f"reviewed example matched sensitive detector ({code}); value was not recorded",
                        line_number,
                    )
                if any(not is_safe_example(code, match.group(0), allowlist) for match in matches):
                    add(findings, "error", "sensitive-content", root, path, f"possible sensitive value ({code})", line_number)


def audit(root: Path) -> list[Finding]:
    findings: FindingList = FindingList()
    root = root.resolve()
    if not root.is_dir():
        return [Finding("error", "root", ".", "project root does not exist")]
    config, config_problems = load_project_config(root)
    for problem in config_problems:
        add(findings, problem.severity, problem.code, root, problem.path, problem.message)
    agents = root / "AGENTS.md"
    docs = config.docs_path(root)
    if canonical_path(root, docs) is None:
        add(findings, "error", "config-docs-root", root, docs, "configured documentation root leaves the project root")
        docs = root / ".r-doc-invalid-docs-root"
    docs_index = docs / "README.md"
    if not agents.is_file():
        add(findings, "error", "missing-entrypoint", root, agents, "project root must contain AGENTS.md")
    if not docs_index.is_file():
        add(findings, "error", "missing-index", root, docs_index, f"project must contain {config.docs_root}/README.md")
    files = markdown_files(docs, root, config)
    root_files = root_markdown_files(root, config)
    note_files: list[Path] = []
    notes_root = config.decision_notes_path(root)
    if config.decision_notes_required:
        if canonical_path(root, notes_root) is None:
            add(findings, "error", "config-decision-notes-root", root, notes_root, "configured decision notes root leaves the project root")
        elif not notes_root.is_dir():
            add(findings, "error", "decision-notes-root-missing", root, notes_root, "configured decision notes root does not exist")
    if canonical_path(root, notes_root) is not None and notes_root.is_dir():
        if not (notes_root / "README.md").is_file():
            add(findings, "error", "decision-notes-index-missing", root, notes_root, "decision notes root must contain README.md")
        note_files = decision_note_files(notes_root, root, config)
    check_files = ([agents] if agents.is_file() else []) + root_files + files + note_files
    outgoing = check_links(root, check_files, findings)
    if note_files:
        check_decision_notes(root, notes_root, note_files, findings, outgoing)
    check_indexes(root, docs, files, outgoing, findings, config, agents)
    check_metadata(root, docs, files, outgoing, findings, config)
    check_sensitive_content(root, check_files, findings, config)
    return findings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit a project's documentation structure without modifying files.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="project root to audit")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument("--stage", help="apply the configured gate for a lifecycle stage")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    findings = audit(args.root)
    config, _ = load_project_config(args.root.resolve())
    if args.stage and (not config.gates or args.stage not in config.gates):
        add(findings, "error", "invalid-stage", args.root.resolve(), config.source or args.root.resolve(), f"stage is not configured: {args.stage}")
    gate = config.gate_for(args.stage)
    errors = [item for item in findings if item.severity == "error"]
    warnings = [item for item in findings if item.severity == "warning"]
    strict = args.strict or gate in {"audit", "blocking"}
    failed = bool(errors or (strict and warnings))
    if args.json:
        print(json.dumps({"status": "fail" if failed else "pass", "errors": len(errors), "warnings": len(warnings), "strict": strict, "stage": args.stage, "gate": gate, "findings": [asdict(item) for item in findings]}, ensure_ascii=False, indent=2))
    else:
        print(f"r-doc audit: {'FAIL' if failed else 'PASS'}")
        for item in findings:
            location = f"{item.path}:{item.line}" if item.line else item.path
            print(f"{item.severity.upper()} {item.code} {location} - {item.message}")
        print(f"errors={len(errors)} warnings={len(warnings)} strict={strict} stage={args.stage or '-'} gate={gate or '-'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
