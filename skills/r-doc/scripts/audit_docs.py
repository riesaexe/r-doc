from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import unquote

import yaml


STATUS_VALUES = {"draft", "proposed", "active", "superseded", "archived"}
SKIP_DIRECTORIES = {".git", ".venv", "node_modules", "dist", "build", "coverage"}
CONFIG_PATHS = (Path(".r-doc.yaml"), Path("docs/r-doc.yaml"), Path("r-doc.yaml"))
CONFIG_KEYS = {
    "version",
    "project_type",
    "docs_root",
    "required_document_types",
    "exclude",
    "gates",
    "relationships",
    "sensitive_allowlist",
}
GATE_VALUES = {"advisory", "audit", "blocking"}
REFERENCE_DEFINITION_PATTERN = re.compile(
    r"(?im)^[ \t]{0,3}\[([^\]]+)\]:[ \t]*(?:<([^>\n]+)>|(\S+))"
)
REFERENCE_LINK_PATTERN = re.compile(r"(?<!\!)!?\[([^\]\n]+)\]\[([^\]\n]*)\]")
SAFE_EXAMPLE_VALUES = {
    "aws-access-key": frozenset({"AKIAIOSFODNN7EXAMPLE"}),
}
SECRET_PATTERNS = (
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private-key-marker"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "aws-access-key"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"), "github-token"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "github-token"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"), "google-api-key"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"), "slack-token"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"), "jwt"),
    (re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"), "openai-api-key"),
    (
        re.compile(
            r"\b(?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?|redis|amqp)://[^/\s:@]+:[^@\s]+@[^)\s]+"
        ),
        "database-connection-string",
    ),
    (
        re.compile(
            r"(?i)\b(?:password|passwd|pwd)\s*[:=]\s*['\"]?"
            r"(?!<|your\b|example\b|sample\b|dummy\b|redacted\b|changeme\b|"
            r"(?:你的|请输入|请填写|请替换|示例|样例|占位符)[^\s'\"]{0,16}(?:密码|口令)|"
            r"(?:待填写|待补充|待设置|未设置)|\*{3,})[^\s'\"]{8,}"
        ),
        "generic-password",
    ),
)
SECRET_CODES = frozenset(code for _, code in SECRET_PATTERNS)


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    path: str
    message: str
    line: int | None = None


@dataclass(frozen=True)
class MarkdownTarget:
    raw_target: str
    line: int
    is_image: bool = False
    is_definition: bool = False
    definition_key: str | None = None


@dataclass(frozen=True)
class TargetReference:
    path: Path | None
    fragment: str | None = None
    fragment_only: bool = False


class FindingList(list[Finding]):
    def __init__(self) -> None:
        super().__init__()
        self._seen: set[Finding] = set()


class FrontmatterParseError(ValueError):
    pass


@dataclass(frozen=True)
class ConfigProblem:
    severity: str
    code: str
    path: Path
    message: str


@dataclass(frozen=True)
class ProjectConfig:
    docs_root: str = "docs"
    exclude: tuple[str, ...] = ()
    required_document_types: tuple[str, ...] = ()
    gates: dict[str, str] | None = None
    relationships: dict[str, tuple[str, ...]] | None = None
    sensitive_allowlist: dict[str, tuple[str, ...]] | None = None
    source: Path | None = None

    def docs_path(self, root: Path) -> Path:
        return root / self.docs_root

    def gate_for(self, stage: str | None) -> str | None:
        if not stage or not self.gates:
            return None
        return self.gates.get(stage)


def relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def canonical_path(root: Path, path: Path) -> Path | None:
    try:
        candidate = path.resolve()
        candidate.relative_to(root.resolve())
    except (OSError, RuntimeError, ValueError):
        return None
    return candidate


def _string_list(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        return None
    return tuple(item.strip() for item in value)


def _config_error(source: Path, code: str, message: str) -> ConfigProblem:
    return ConfigProblem("error", code, source, message)


def load_project_config(root: Path) -> tuple[ProjectConfig, list[ConfigProblem]]:
    candidates = [root / relative_path for relative_path in CONFIG_PATHS]
    existing = [path for path in candidates if path.is_file()]
    if not existing:
        return ProjectConfig(), []

    source = existing[0]
    problems: list[ConfigProblem] = []
    if len(existing) > 1:
        listed = ", ".join(relative(root, path) for path in existing)
        problems.append(_config_error(source, "config-duplicate", f"multiple project configuration files found: {listed}"))

    try:
        values = yaml.load(source.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        problems.append(_config_error(source, "config-parse", f"could not parse project configuration: {error}"))
        return ProjectConfig(source=source), problems
    if values is None:
        values = {}
    if not isinstance(values, dict):
        problems.append(_config_error(source, "config-parse", "project configuration must contain a YAML mapping"))
        return ProjectConfig(source=source), problems

    unknown = sorted(str(key) for key in values if key not in CONFIG_KEYS)
    if unknown:
        problems.append(_config_error(source, "config-unknown", f"unsupported configuration field(s): {', '.join(unknown)}"))

    docs_root = "docs"
    if "version" in values and values["version"] not in {"1", 1}:
        problems.append(_config_error(source, "config-version", f"unsupported configuration version: {values['version']!r}"))
    if "project_type" in values and not isinstance(values["project_type"], str):
        problems.append(_config_error(source, "config-project-type", "project_type must be a string"))
    raw_docs_root = values.get("docs_root", docs_root)
    if not isinstance(raw_docs_root, str) or not raw_docs_root.strip():
        problems.append(_config_error(source, "config-docs-root", "docs_root must be a non-empty relative path"))
    else:
        normalized_docs_root = raw_docs_root.strip().replace("\\", "/").strip("/")
        docs_root_path = PurePosixPath(normalized_docs_root)
        if (docs_root_path.is_absolute() or PureWindowsPath(normalized_docs_root).is_absolute() or ".." in docs_root_path.parts or normalized_docs_root in {"", "."}):
            problems.append(_config_error(source, "config-docs-root", "docs_root must stay inside the project root"))
        else:
            docs_root = normalized_docs_root

    exclude: tuple[str, ...] = ()
    if "exclude" in values:
        parsed_exclude = _string_list(values["exclude"])
        if parsed_exclude is None:
            problems.append(_config_error(source, "config-exclude", "exclude must be a list of non-empty strings"))
        else:
            exclude = tuple(item.replace("\\", "/").strip("/") for item in parsed_exclude)

    required_document_types: tuple[str, ...] = ()
    if "required_document_types" in values:
        parsed_types = _string_list(values["required_document_types"])
        if parsed_types is None:
            problems.append(_config_error(source, "config-required-types", "required_document_types must be a list of non-empty strings"))
        else:
            required_document_types = parsed_types

    gates: dict[str, str] | None = None
    if "gates" in values:
        raw_gates = values["gates"]
        if not isinstance(raw_gates, dict):
            problems.append(_config_error(source, "config-gates", "gates must be a mapping of stage names to gate strengths"))
        else:
            gates = {}
            for stage, gate in raw_gates.items():
                if not isinstance(stage, str) or not isinstance(gate, str) or gate not in GATE_VALUES:
                    problems.append(_config_error(source, "config-gates", f"invalid gate for {stage!r}: {gate!r}"))
                    continue
                gates[stage] = gate

    relationships: dict[str, tuple[str, ...]] | None = None
    if "relationships" in values:
        raw_relationships = values["relationships"]
        if not isinstance(raw_relationships, dict):
            problems.append(_config_error(source, "config-relationships", "relationships must be a mapping"))
        else:
            raw_requirements = raw_relationships.get("require_for", raw_relationships)
            if not isinstance(raw_requirements, dict):
                problems.append(_config_error(source, "config-relationships", "relationships.require_for must be a mapping"))
            else:
                relationships = {}
                for document_type, targets in raw_requirements.items():
                    parsed_targets = _string_list(targets)
                    if not isinstance(document_type, str) or parsed_targets is None:
                        problems.append(_config_error(source, "config-relationships", f"invalid relationship requirement: {document_type!r}"))
                        continue
                    relationships[document_type] = parsed_targets

    sensitive_allowlist: dict[str, tuple[str, ...]] | None = None
    if "sensitive_allowlist" in values:
        raw_allowlist = values["sensitive_allowlist"]
        if not isinstance(raw_allowlist, dict):
            problems.append(_config_error(source, "config-sensitive-allowlist", "sensitive_allowlist must be a mapping of detector codes to exact example values"))
        else:
            sensitive_allowlist = {}
            for code, raw_values in raw_allowlist.items():
                parsed_values = _string_list(raw_values)
                if not isinstance(code, str) or code not in SECRET_CODES:
                    problems.append(_config_error(source, "config-sensitive-allowlist", f"unsupported sensitive detector code: {code!r}"))
                    continue
                if parsed_values is None:
                    problems.append(_config_error(source, "config-sensitive-allowlist", f"allowlist values for {code} must be a list of non-empty strings"))
                    continue
                sensitive_allowlist[code] = parsed_values

    return ProjectConfig(
        docs_root=docs_root,
        exclude=exclude,
        required_document_types=required_document_types,
        gates=gates,
        relationships=relationships,
        sensitive_allowlist=sensitive_allowlist,
        source=source,
    ), problems


def path_is_excluded(root: Path, path: Path, config: ProjectConfig) -> bool:
    try:
        relative_path = path.relative_to(root)
    except ValueError:
        return True
    parts = relative_path.parts
    if any(part in SKIP_DIRECTORIES for part in parts):
        return True
    candidate = PurePosixPath(relative_path.as_posix())
    for raw_pattern in config.exclude:
        pattern = raw_pattern.replace("\\", "/").strip("/")
        if not pattern:
            continue
        pattern_path = PurePosixPath(pattern)
        if candidate == pattern_path or candidate.is_relative_to(pattern_path):
            return True
        if candidate.match(pattern) or any(part == pattern for part in parts):
            return True
    return False


def is_safe_example(code: str, value: str, allowlist: dict[str, tuple[str, ...]] | None = None) -> bool:
    built_in = SAFE_EXAMPLE_VALUES.get(code, ())
    configured = (allowlist or {}).get(code, ())
    return value in built_in or value in configured


def add(finding_list: list[Finding], severity: str, code: str, root: Path, path: Path, message: str, line: int | None = None) -> None:
    finding = Finding(severity, code, relative(root, path), message, line)
    if isinstance(finding_list, FindingList):
        if finding in finding_list._seen:
            return
        finding_list._seen.add(finding)
    elif finding in finding_list:
        return
    finding_list.append(finding)


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


def read_text(path: Path, root: Path, findings: list[Finding]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        add(findings, "error", "encoding", root, path, f"not valid UTF-8: {error}")
    except OSError as error:
        add(findings, "error", "read-error", root, path, str(error))
    return ""


def parse_frontmatter(text: str) -> tuple[dict[str, object], int]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, 0
    end = next((index for index in range(1, len(lines)) if lines[index].strip() == "---"), -1)
    if end < 0:
        raise FrontmatterParseError("frontmatter closing delimiter is missing")
    try:
        values = yaml.load("\n".join(lines[1:end]), Loader=yaml.BaseLoader)
    except yaml.YAMLError as error:
        raise FrontmatterParseError(str(error)) from error
    if values is None:
        return {}, end + 1
    if not isinstance(values, dict):
        raise FrontmatterParseError("frontmatter must contain a YAML mapping")
    return values, end + 1


def _blank_range(chars: list[str], start: int, end: int) -> None:
    for index in range(start, end):
        if chars[index] != "\n":
            chars[index] = " "


def _fence_marker(line: str) -> tuple[str, int] | None:
    match = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
    if not match:
        return None
    marker = match.group(1)
    return marker[0], len(marker)


def mask_markdown_non_link_regions(text: str) -> str:
    chars = list(text)
    active_fence: tuple[str, int] | None = None
    offset = 0
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        marker = _fence_marker(body)
        if active_fence is not None:
            _blank_range(chars, offset, offset + len(body))
            fence_char, fence_length = active_fence
            if re.match(rf"^ {{0,3}}{re.escape(fence_char)}{{{fence_length},}}[ \t]*$", body):
                active_fence = None
        elif marker is not None:
            _blank_range(chars, offset, offset + len(body))
            active_fence = marker
        offset += len(line)

    masked = "".join(chars)
    cursor = 0
    while True:
        start = masked.find("<!--", cursor)
        if start < 0:
            break
        end_marker = masked.find("-->", start + 4)
        end = len(masked) if end_marker < 0 else end_marker + 3
        _blank_range(chars, start, end)
        masked = "".join(chars)
        cursor = end

    cursor = 0
    while cursor < len(masked):
        if masked[cursor] != "`":
            cursor += 1
            continue
        run_end = cursor
        while run_end < len(masked) and masked[run_end] == "`":
            run_end += 1
        run = masked[cursor:run_end]
        close = masked.find(run, run_end)
        if close < 0:
            cursor = run_end
            continue
        _blank_range(chars, cursor, close + len(run))
        masked = "".join(chars)
        cursor = close + len(run)
    return "".join(chars)


def target_reference(source: Path, raw_target: str, root: Path) -> TargetReference | None:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    else:
        target = target.split()[0] if target else ""
    if not target:
        return None
    lowered = target.lower()
    if lowered.startswith(("http://", "https://", "ftp://", "mailto:", "data:", "//")):
        return None
    fragment: str | None = None
    if "#" in target:
        target, fragment = target.split("#", 1)
        fragment = unquote(fragment)
    target = unquote(target.split("?", 1)[0])
    if not target:
        return TargetReference(source, fragment, fragment_only=True) if fragment is not None else None
    path = (root / target.lstrip("/")) if target.startswith("/") else (source.parent / target)
    return TargetReference(path, fragment)


def target_path(source: Path, raw_target: str, root: Path) -> Path | None:
    reference = target_reference(source, raw_target, root)
    return reference.path if reference is not None else None


def markdown_targets(text: str) -> list[MarkdownTarget]:
    lexical_text = mask_markdown_non_link_regions(text)
    targets: list[tuple[int, MarkdownTarget]] = []
    definitions: dict[str, str] = {}
    definition_spans: list[tuple[int, int]] = []
    for match in REFERENCE_DEFINITION_PATTERN.finditer(lexical_text):
        raw_target = None
        for group in (2, 3):
            start, end = match.span(group)
            if start >= 0:
                raw_target = text[start:end]
                break
        if raw_target:
            key = " ".join(match.group(1).split()).casefold()
            definitions[key] = raw_target
            line = text.count("\n", 0, match.start()) + 1
            targets.append((match.start(), MarkdownTarget(raw_target, line, is_definition=True, definition_key=key)))
            definition_spans.append((match.start(), match.end()))

    inline_start = re.compile(r"(?<!\!)!?\[[^\]\n]+\]\(")
    for match in inline_start.finditer(lexical_text):
        cursor = match.end()
        if cursor < len(lexical_text) and lexical_text[cursor] == "<":
            end = lexical_text.find(">", cursor + 1)
            if end < 0 or end + 1 >= len(lexical_text) or lexical_text[end + 1] != ")":
                continue
            raw_target = text[cursor + 1 : end]
            close = end + 1
        else:
            depth = 0
            escaped = False
            close = -1
            while cursor < len(lexical_text):
                character = lexical_text[cursor]
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == "(":
                    depth += 1
                elif character == ")":
                    if depth == 0:
                        close = cursor
                        break
                    depth -= 1
                cursor += 1
            if close < 0:
                continue
            raw_target = text[match.end() : close]
        line = text.count("\n", 0, match.start()) + 1
        targets.append((match.start(), MarkdownTarget(raw_target, line, is_image=text[match.start()] == "!")))

    for match in REFERENCE_LINK_PATTERN.finditer(lexical_text):
        key = " ".join((match.group(2) or match.group(1)).split()).casefold()
        raw_target = definitions.get(key)
        if raw_target:
            line = text.count("\n", 0, match.start()) + 1
            targets.append(
                (
                    match.start(),
                    MarkdownTarget(raw_target, line, is_image=text[match.start()] == "!", definition_key=key),
                )
            )

    for match in re.finditer(r"(?<!\!)!?\[([^\]\n]+)\]", lexical_text):
        after = lexical_text[match.end()] if match.end() < len(lexical_text) else ""
        before = text[match.start() - 1] if match.start() else ""
        if after in "([:":
            continue
        if before in "](" or any(start <= match.start() < end for start, end in definition_spans):
            continue
        key = " ".join(match.group(1).split()).casefold()
        raw_target = definitions.get(key)
        if raw_target:
            line = text.count("\n", 0, match.start()) + 1
            targets.append(
                (
                    match.start(),
                    MarkdownTarget(raw_target, line, is_image=text[match.start()] == "!", definition_key=key),
                )
            )

    seen: set[tuple[int, str, bool, bool]] = set()
    result: list[MarkdownTarget] = []
    for position, target in sorted(targets, key=lambda item: item[0]):
        marker = (position, target.raw_target, target.is_image, target.is_definition)
        if marker not in seen:
            result.append(target)
            seen.add(marker)
    return result


def validation_targets(text: str) -> list[MarkdownTarget]:
    targets = markdown_targets(text)
    used_definitions = {target.definition_key for target in targets if not target.is_definition and target.definition_key}
    return [target for target in targets if not target.is_definition or target.definition_key not in used_definitions]


def navigation_targets(text: str) -> list[MarkdownTarget]:
    return [target for target in markdown_targets(text) if not target.is_definition and not target.is_image]


def _anchor_slug(value: str) -> str:
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = re.sub(r"<[^>]+>", "", value)
    value = unicodedata.normalize("NFKC", value).casefold()
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE)
    return re.sub(r"[-\s]+", "-", value).strip("-")


def markdown_anchors(path: Path, root: Path, findings: list[Finding]) -> set[str]:
    text = read_text(path, root, findings)
    lexical_lines = mask_markdown_non_link_regions(text).splitlines()
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    for line, lexical_line in zip(text.splitlines(), lexical_lines):
        if not lexical_line.strip():
            continue
        lexical_match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", lexical_line)
        original_match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not lexical_match or not original_match:
            continue
        slug = _anchor_slug(original_match.group(1))
        if not slug:
            continue
        index = counts.get(slug, 0)
        counts[slug] = index + 1
        anchors.add(slug if index == 0 else f"{slug}-{index}")
    return anchors


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
                normalized_anchors = {anchor.casefold() for anchor in anchors}
                if reference.fragment.casefold() not in normalized_anchors and normalized_fragment.casefold() not in normalized_anchors:
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
                if any(not is_safe_example(code, match.group(0), config.sensitive_allowlist if config else None) for match in pattern.finditer(line)):
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
    check_files = ([agents] if agents.is_file() else []) + root_files + files
    outgoing = check_links(root, check_files, findings)
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
