from __future__ import annotations

from datetime import date
from dataclasses import dataclass
from pathlib import Path
import re

from .config import ProjectConfig, _string_list, canonical_path, path_is_excluded, relative
from .io import add, read_text
from .markdown import parse_frontmatter
from .models import Finding, FrontmatterParseError


NOTE_LIFECYCLES = {"proposed", "implemented", "rejected", "archived"}
NOTE_CLASSES = {"feature", "bug-fix", "simplification", "architecture", "process", "testing"}
ARCHIVABLE_LIFECYCLES = {"proposed", "implemented", "rejected"}
REQUIRED_FIELDS = ("id", "type", "status", "title", "created", "updated")
COMMON_SECTIONS = ("problem", "alternatives considered")
LIFECYCLE_SECTIONS = {
    "proposed": ("proposal", "acceptance criteria", "risks"),
    "implemented": ("decision", "consequences"),
    "rejected": ("proposal", "rejection reason"),
}
IMPLEMENTED_FORBIDDEN_SECTIONS = {"proposal", "plan", "migration plan", "acceptance criteria"}


@dataclass(frozen=True)
class ArchivePlan:
    source: Path
    destination: Path
    before: str
    after: str
    identifier: str


def decision_note_files(notes_root: Path, root: Path, config: ProjectConfig) -> list[Path]:
    if not notes_root.is_dir():
        return []
    return sorted(
        (
            path
            for path in notes_root.rglob("*.md")
            if path.is_file() and not path_is_excluded(root, path, config)
        ),
        key=lambda path: relative(root, path),
    )


def _parse_iso_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _first_heading(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _heading_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().rstrip("#").strip()).casefold()


def _sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^#{2,6}\s+(.+?)\s*$", text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[_heading_key(match.group(1))] = text[start:end].strip()
    return sections


def _check_relationships(root: Path, path: Path, values: dict[str, object], findings: list[Finding]) -> None:
    for key in ("related_docs", "related_code", "planned_code"):
        if key in values and _string_list(values[key]) is None:
            add(findings, "error", "decision-note-relationship", root, path, f"{key} must be a list of non-empty strings")

    supersedes = values.get("supersedes")
    if supersedes is not None and (not isinstance(supersedes, str) or not supersedes.strip()):
        add(findings, "error", "decision-note-relationship", root, path, "supersedes must be a non-empty document ID")

    related_code = values.get("related_code")
    if isinstance(related_code, list):
        for code_path in related_code:
            if not isinstance(code_path, str):
                continue
            canonical = canonical_path(root, root / code_path)
            if canonical is None:
                add(findings, "error", "decision-note-related-code-outside-root", root, path, f"related_code leaves the project root: {code_path}")
            elif not canonical.is_file():
                add(findings, "error", "decision-note-related-code-missing", root, path, f"related_code target is not an existing file: {code_path}")

    planned_code = values.get("planned_code")
    if isinstance(planned_code, list):
        for code_path in planned_code:
            if isinstance(code_path, str) and canonical_path(root, root / code_path) is None:
                add(findings, "error", "decision-note-planned-code-outside-root", root, path, f"planned_code leaves the project root: {code_path}")


def _check_sections(root: Path, path: Path, text: str, lifecycle: str, findings: list[Finding]) -> None:
    sections = _sections(text)
    required = COMMON_SECTIONS + LIFECYCLE_SECTIONS.get(lifecycle, ())
    for heading in required:
        body = sections.get(heading)
        if body is None:
            add(findings, "error", "decision-note-section-missing", root, path, f"decision note is missing required section: {heading}")
        elif not body.strip():
            add(findings, "error", "decision-note-section-empty", root, path, f"decision note section is empty: {heading}")

    if lifecycle == "implemented":
        for heading in sorted(IMPLEMENTED_FORBIDDEN_SECTIONS.intersection(sections)):
            add(
                findings,
                "error",
                "decision-note-implemented-proposal-heading",
                root,
                path,
                f"implemented decision note still contains proposal-era section: {heading}",
            )


def _check_supersession_relations(
    root: Path,
    records: dict[str, tuple[Path, dict[str, object]]],
    outgoing: dict[Path, set[Path]] | None,
    findings: list[Finding],
) -> None:
    edges: dict[str, str] = {}
    for identifier, (path, values) in records.items():
        target = values.get("supersedes")
        if not isinstance(target, str) or not target.strip():
            continue
        target = target.strip()
        if target == identifier:
            add(findings, "error", "decision-note-supersedes-self", root, path, "decision note cannot supersede itself")
            continue
        successor = records.get(target)
        if successor is None:
            if target.upper().startswith("DEC-"):
                add(findings, "error", "decision-note-supersedes-missing", root, path, f"superseded decision note ID does not exist: {target}")
            continue
        edges[identifier] = target
        if outgoing is not None:
            source_path = canonical_path(root, path) or path
            target_path = canonical_path(root, successor[0]) or successor[0]
            if target_path not in outgoing.get(source_path, set()):
                add(findings, "error", "decision-note-supersedes-unlinked", root, path, f"decision note does not link to its superseded note: {target}")

    cycles: set[frozenset[str]] = set()
    for identifier in edges:
        chain: list[str] = []
        current = identifier
        while current in edges:
            if current in chain:
                cycle = frozenset(chain[chain.index(current):])
                if cycle not in cycles:
                    cycles.add(cycle)
                    add(
                        findings,
                        "error",
                        "decision-note-supersedes-cycle",
                        root,
                        records[current][0],
                        f"decision note supersession cycle includes: {', '.join(sorted(cycle))}",
                    )
                break
            chain.append(current)
            current = edges[current]


def check_decision_notes(
    root: Path,
    notes_root: Path,
    files: list[Path],
    findings: list[Finding],
    outgoing: dict[Path, set[Path]] | None = None,
) -> None:
    seen_ids: dict[str, Path] = {}
    records: dict[str, tuple[Path, dict[str, object]]] = {}
    for path in files:
        if path == notes_root / "README.md":
            continue

        try:
            parts = path.relative_to(notes_root).parts
        except ValueError:
            add(findings, "error", "decision-note-path", root, path, "decision note is outside the configured notes root")
            continue
        if len(parts) != 3 or parts[0] not in NOTE_LIFECYCLES or parts[1] not in NOTE_CLASSES:
            add(
                findings,
                "error",
                "decision-note-path",
                root,
                path,
                "decision note path must be <lifecycle>/<class>/<slug>.md",
            )
            continue

        text = read_text(path, root, findings)
        try:
            values, _ = parse_frontmatter(text)
        except FrontmatterParseError as error:
            add(findings, "error", "decision-note-frontmatter-parse", root, path, str(error))
            continue
        if not values:
            add(findings, "error", "decision-note-frontmatter", root, path, "decision note must contain frontmatter")
            continue

        for key in REQUIRED_FIELDS:
            value = values.get(key)
            if not isinstance(value, str) or not value.strip():
                add(findings, "error", "decision-note-field", root, path, f"missing frontmatter field: {key}")

        if values.get("type") != "decision":
            add(findings, "error", "decision-note-type", root, path, "decision note type must be: decision")

        lifecycle = parts[0]
        status = values.get("status")
        if not isinstance(status, str) or status not in NOTE_LIFECYCLES:
            add(findings, "error", "decision-note-status", root, path, f"unsupported decision note status: {status}")
        elif status != lifecycle:
            add(findings, "error", "decision-note-status-path", root, path, f"note status {status!r} does not match lifecycle directory {lifecycle!r}")

        parsed_dates: dict[str, date] = {}
        for key in ("created", "updated", "review_after", "archived"):
            value = values.get(key, "")
            if value:
                parsed = _parse_iso_date(value)
                if parsed is None:
                    add(findings, "error", "decision-note-date", root, path, f"invalid {key} date: {value}")
                else:
                    parsed_dates[key] = parsed
        if "created" in parsed_dates and "updated" in parsed_dates and parsed_dates["updated"] < parsed_dates["created"]:
            add(findings, "error", "decision-note-date-order", root, path, "updated date is earlier than created date")
        if "review_after" in parsed_dates and parsed_dates["review_after"] < date.today():
            add(findings, "warning", "decision-note-review-overdue", root, path, f"review_after date has passed: {values['review_after']}")
        if status == "archived" and "archived" not in parsed_dates:
            add(findings, "error", "decision-note-archive-date", root, path, "archived decision note must contain a valid archived date")

        title = values.get("title")
        heading = _first_heading(text)
        if not heading:
            add(findings, "error", "decision-note-title", root, path, "decision note must contain a first-level title")
        elif isinstance(title, str) and title.strip() != heading:
            add(findings, "error", "decision-note-title", root, path, f"frontmatter title does not match the first H1: {title!r} != {heading!r}")

        identifier = values.get("id")
        if isinstance(identifier, str) and identifier.strip():
            identifier = identifier.strip()
            if identifier in seen_ids:
                add(findings, "error", "decision-note-duplicate-id", root, path, f"ID also used by {relative(root, seen_ids[identifier])}: {identifier}")
            else:
                seen_ids[identifier] = path
                records[identifier] = (path, values)

        _check_relationships(root, path, values, findings)
        if isinstance(status, str) and status in NOTE_LIFECYCLES:
            _check_sections(root, path, text, lifecycle, findings)

    _check_supersession_relations(root, records, outgoing, findings)


def _update_frontmatter_scalars(text: str, updates: dict[str, str]) -> str:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError("decision note must contain frontmatter")
    closing = next((index for index in range(1, len(lines)) if lines[index].strip() == "---"), -1)
    if closing < 0:
        raise ValueError("decision note frontmatter is not closed")
    body = lines[1:closing]
    newline = "\r\n" if any(line.endswith("\r\n") for line in body) else "\n"
    for key, value in updates.items():
        pattern = re.compile(rf"^{re.escape(key)}\s*:")
        index = next((index for index, line in enumerate(body) if pattern.match(line)), None)
        if index is not None:
            ending = "\r\n" if body[index].endswith("\r\n") else "\n" if body[index].endswith("\n") else ""
            body[index] = f"{key}: {value}{ending}"
            continue
        insert_at = next((index + 1 for index, line in enumerate(body) if re.match(r"^updated\s*:", line)), len(body))
        body.insert(insert_at, f"{key}: {value}{newline}")
    return "".join([lines[0], *body, lines[closing], *lines[closing + 1:]])


def plan_archive(root: Path, config: ProjectConfig, note_path: Path, today: date | None = None) -> ArchivePlan:
    root = root.resolve()
    notes_root = config.decision_notes_path(root)
    canonical_notes_root = canonical_path(root, notes_root)
    if canonical_notes_root is None or not canonical_notes_root.is_dir():
        raise ValueError("decision notes root does not exist inside the project root")
    candidate = note_path if note_path.is_absolute() else root / note_path
    canonical_candidate = canonical_path(root, candidate)
    if canonical_candidate is None or not canonical_candidate.is_file():
        raise ValueError(f"decision note does not exist inside the project root: {note_path}")
    try:
        parts = canonical_candidate.relative_to(canonical_notes_root).parts
    except ValueError as error:
        raise ValueError("decision note is outside the configured notes root") from error
    if len(parts) != 3 or parts[0] not in ARCHIVABLE_LIFECYCLES or parts[1] not in NOTE_CLASSES or canonical_candidate.suffix.lower() != ".md":
        raise ValueError("archive target must be <proposed|implemented|rejected>/<class>/<slug>.md")
    text = canonical_candidate.read_text(encoding="utf-8")
    values, _ = parse_frontmatter(text)
    if not values or values.get("type") != "decision":
        raise ValueError("archive target must be a decision note with valid frontmatter")
    if values.get("status") != parts[0]:
        raise ValueError("decision note status must match its lifecycle directory before archiving")
    identifier = values.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("archive target must contain a non-empty decision note ID")
    destination = canonical_notes_root / "archived" / parts[1] / parts[2]
    if destination.exists():
        raise ValueError(f"archive destination already exists: {relative(root, destination)}")
    archive_date = (today or date.today()).isoformat()
    updated = _update_frontmatter_scalars(text, {"status": "archived", "updated": archive_date, "archived": archive_date})
    return ArchivePlan(canonical_candidate, destination, text, updated, identifier.strip())


def apply_archive(plan: ArchivePlan) -> None:
    if not plan.source.is_file():
        raise ValueError(f"archive source disappeared: {plan.source}")
    if plan.source.read_text(encoding="utf-8") != plan.before:
        raise ValueError(f"archive source changed after planning: {plan.source}")
    if plan.destination.exists():
        raise ValueError(f"archive destination appeared after planning: {plan.destination}")
    plan.destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        plan.destination.write_text(plan.after, encoding="utf-8")
        plan.source.unlink()
    except OSError:
        if plan.destination.is_file() and plan.source.is_file():
            try:
                plan.destination.unlink()
            except OSError:
                pass
        raise
