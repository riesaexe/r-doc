from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import unquote

import yaml


STATUS_VALUES = {"draft", "proposed", "active", "superseded", "archived"}
SKIP_DIRECTORIES = {".git", ".venv", "node_modules", "dist", "build", "coverage"}
LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
SECRET_PATTERNS = (
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private-key-marker"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "aws-access-key"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"), "github-token"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "github-token"),
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


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    path: str
    message: str
    line: int | None = None


class FrontmatterParseError(ValueError):
    pass


def relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def add(finding_list: list[Finding], severity: str, code: str, root: Path, path: Path, message: str, line: int | None = None) -> None:
    finding_list.append(Finding(severity, code, relative(root, path), message, line))


def markdown_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    paths: list[Path] = []
    for path in directory.rglob("*.md"):
        if any(part in SKIP_DIRECTORIES for part in path.parts):
            continue
        paths.append(path)
    return sorted(paths)


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


def target_path(source: Path, raw_target: str, root: Path) -> Path | None:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    else:
        target = target.split()[0] if target else ""
    if not target or target.startswith("#"):
        return None
    lowered = target.lower()
    if lowered.startswith(("http://", "https://", "ftp://", "mailto:", "data:", "//")):
        return None
    target = unquote(target.split("#", 1)[0].split("?", 1)[0])
    if not target:
        return None
    return (root / target.lstrip("/")) if target.startswith("/") else (source.parent / target)


def check_links(root: Path, files: list[Path], findings: list[Finding]) -> dict[Path, set[Path]]:
    outgoing: dict[Path, set[Path]] = {}
    for path in files:
        text = read_text(path, root, findings)
        targets: set[Path] = set()
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in LINK_PATTERN.finditer(line):
                resolved = target_path(path, match.group(1), root)
                if resolved is None:
                    continue
                try:
                    resolved.relative_to(root)
                except ValueError:
                    add(findings, "error", "link-outside-root", root, path, f"link leaves the project root: {match.group(1)}", line_number)
                    continue
                if resolved.is_dir():
                    resolved = resolved / "README.md"
                targets.add(resolved)
                if not resolved.exists():
                    add(findings, "error", "broken-link", root, path, f"target does not exist: {match.group(1)}", line_number)
        outgoing[path] = targets
    return outgoing


def check_indexes(root: Path, docs: Path, files: list[Path], outgoing: dict[Path, set[Path]], findings: list[Finding]) -> None:
    if not docs.is_dir():
        return
    for directory in sorted(path for path in docs.rglob("*") if path.is_dir()):
        if any(part in SKIP_DIRECTORIES for part in directory.parts):
            continue
        if any(path.is_file() for path in directory.rglob("*.md")) and not (directory / "README.md").exists():
            add(findings, "error", "missing-nested-index", root, directory, "directory contains Markdown documents but no README.md")

    incoming: dict[Path, int] = {path: 0 for path in files if path != docs / "README.md"}
    index_files = [path for path in files if path.name == "README.md"]
    index_files.extend(path for path in [root / "AGENTS.md"] if path.exists())
    for index in index_files:
        for target in outgoing.get(index, set()):
            if target in incoming:
                incoming[target] += 1
    for path, count in incoming.items():
        if count == 0:
            add(findings, "error", "unindexed-document", root, path, "document is not reachable from AGENTS.md or an index README.md")


def check_metadata(root: Path, docs: Path, files: list[Path], findings: list[Finding]) -> None:
    seen_ids: dict[str, Path] = {}
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
        for key in ("id", "type", "status", "title", "created", "updated"):
            value = values.get(key)
            if not isinstance(value, str) or not value.strip():
                add(findings, "error", "metadata-field", root, path, f"missing frontmatter field: {key}")
        status = values.get("status")
        if status and (not isinstance(status, str) or status not in STATUS_VALUES):
            add(findings, "error", "metadata-status", root, path, f"unsupported status: {status}")
        for key in ("created", "updated"):
            value = values.get(key, "")
            if value and (not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T.*)?", value)):
                add(findings, "error", "metadata-date", root, path, f"invalid {key} date: {value}")
        identifier = values.get("id")
        if isinstance(identifier, str) and identifier:
            if identifier in seen_ids:
                add(findings, "error", "duplicate-id", root, path, f"ID also used by {relative(root, seen_ids[identifier])}: {identifier}")
            else:
                seen_ids[identifier] = path


def check_sensitive_content(root: Path, files: list[Path], findings: list[Finding]) -> None:
    for path in files:
        text = read_text(path, root, findings)
        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern, code in SECRET_PATTERNS:
                if pattern.search(line):
                    add(findings, "error", "sensitive-content", root, path, f"possible sensitive value ({code})", line_number)


def audit(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    root = root.resolve()
    if not root.is_dir():
        return [Finding("error", "root", ".", "project root does not exist")]
    agents = root / "AGENTS.md"
    docs = root / "docs"
    docs_index = docs / "README.md"
    if not agents.is_file():
        add(findings, "error", "missing-entrypoint", root, agents, "project root must contain AGENTS.md")
    if not docs_index.is_file():
        add(findings, "error", "missing-index", root, docs_index, "project must contain docs/README.md")
    files = markdown_files(docs)
    check_files = ([agents] if agents.is_file() else []) + files
    outgoing = check_links(root, check_files, findings)
    check_indexes(root, docs, files, outgoing, findings)
    check_metadata(root, docs, files, findings)
    check_sensitive_content(root, check_files, findings)
    return findings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit a project's documentation structure without modifying files.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="project root to audit")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    findings = audit(args.root)
    errors = [item for item in findings if item.severity == "error"]
    warnings = [item for item in findings if item.severity == "warning"]
    failed = bool(errors or (args.strict and warnings))
    if args.json:
        print(json.dumps({"status": "fail" if failed else "pass", "errors": len(errors), "warnings": len(warnings), "findings": [asdict(item) for item in findings]}, ensure_ascii=False, indent=2))
    else:
        print(f"r-doc audit: {'FAIL' if failed else 'PASS'}")
        for item in findings:
            location = f"{item.path}:{item.line}" if item.line else item.path
            print(f"{item.severity.upper()} {item.code} {location} - {item.message}")
        print(f"errors={len(errors)} warnings={len(warnings)} strict={args.strict}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
