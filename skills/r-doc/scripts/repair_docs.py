from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from audit_docs import LINK_PATTERN, SKIP_DIRECTORIES, target_path


@dataclass(frozen=True)
class RepairAction:
    kind: str
    path: str
    detail: str
    content: str
    before: str = ""


class RepairConflict(Exception):
    pass


def relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def inside(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def has_markdown(directory: Path) -> bool:
    if not directory.is_dir():
        return False
    for path in directory.rglob("*.md"):
        if not any(part in SKIP_DIRECTORIES for part in path.parts):
            return True
    return False


def markdown_direct_children(directory: Path) -> list[Path]:
    return sorted(path for path in directory.glob("*.md") if path.name != "README.md")


def document_label(path: Path) -> str:
    if path.is_file():
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                match = re.match(r"^#\s+(.+?)\s*$", line)
                if match:
                    return match.group(1)
        except (OSError, UnicodeDecodeError):
            pass
    return path.stem.replace("-", " ").replace("_", " ").title()


def directory_entries(directory: Path) -> list[tuple[str, str]]:
    entries = [(document_label(path), path.name) for path in markdown_direct_children(directory)]
    for child in sorted(path for path in directory.iterdir() if path.is_dir() and not path.is_symlink() and path.name not in SKIP_DIRECTORIES):
        if has_markdown(child):
            label = document_label(child / "README.md") if (child / "README.md").is_file() else child.name.replace("-", " ").replace("_", " ").title()
            entries.append((label, f"{child.name}/README.md"))
    return entries


def index_content(directory: Path, entries: list[tuple[str, str]], root: Path) -> str:
    if directory == root / "docs":
        title = "Documentation index"
        parent_link = "../AGENTS.md"
        parent_label = "Project entrypoint"
    else:
        title = f"{directory.name.replace('-', ' ').replace('_', ' ').title()} documentation index"
        parent_link = "../README.md"
        parent_label = "Parent index"
    lines = [
        f"# {title}",
        "",
        "## Scope",
        "",
        f"This index organizes the documentation maintained under `{directory.name}/`.",
        "",
        "## Documents",
        "",
    ]
    if entries:
        lines.extend(f"- [{label}]({target})" for label, target in entries)
    else:
        lines.append("- No topic documents are indexed yet.")
    lines.extend(["", f"## {parent_label}", "", f"[{parent_label}]({parent_link})", ""])
    return "\n".join(lines)


def agent_content() -> str:
    return "\n".join(
        [
            "# Project documentation entrypoint",
            "",
            "This is a generated navigation skeleton. Complete project-specific commands, rules, and routes after reviewing the repository.",
            "",
            "## Quick start",
            "",
            "1. Read this file;",
            "2. Read [docs/README.md](docs/README.md);",
            "3. Follow the relevant topic index;",
            "4. Run the project's validation and test commands before declaring work complete.",
            "",
            "## Context-loading order",
            "",
            "```text",
            "AGENTS.md",
            "→ docs/README.md",
            "→ relevant topic README.md",
            "→ target document",
            "```",
            "",
            "## Documentation index",
            "",
            "Start with [docs/README.md](docs/README.md). Keep detailed project knowledge in docs/.",
            "",
        ]
    )


def linked_targets(path: Path, root: Path) -> set[Path]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    targets: set[Path] = set()
    for match in LINK_PATTERN.finditer(text):
        target = target_path(path, match.group(1), root)
        if target is not None:
            targets.add(target.resolve())
    return targets


def append_missing_links(path: Path, root: Path, entries: list[tuple[str, str]]) -> str | None:
    before = path.read_text(encoding="utf-8")
    linked = linked_targets(path, root)
    missing = [(label, target) for label, target in entries if (path.parent / target).resolve() not in linked]
    if not missing:
        return None
    lines = [before.rstrip(), ""]
    if "## Document links" not in before:
        lines.extend(["## Document links", ""])
    lines.extend(f"- [{label}]({target})" for label, target in missing)
    lines.append("")
    return "\n".join(lines)


def append_agent_link(path: Path, root: Path) -> str | None:
    before = path.read_text(encoding="utf-8")
    target = (root / "docs" / "README.md").resolve()
    if target in linked_targets(path, root):
        return None
    lines = [before.rstrip(), ""]
    if "## Documentation index" not in before:
        lines.extend(["## Documentation index", ""])
    lines.extend(["[Documentation index](docs/README.md)", ""])
    return "\n".join(lines)


def plan_repairs(root: Path) -> list[RepairAction]:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"project root does not exist: {root}")
    agents = root / "AGENTS.md"
    docs = root / "docs"
    docs_index = docs / "README.md"
    if docs.is_symlink() and not inside(root, docs):
        raise ValueError("docs directory points outside the project root")
    actions: list[RepairAction] = []
    if not agents.exists():
        actions.append(RepairAction("create", relative(root, agents), "create missing project entrypoint", agent_content()))
    if not docs_index.exists():
        entries = directory_entries(docs) if docs.is_dir() else []
        actions.append(RepairAction("create", relative(root, docs_index), "create missing documentation index", index_content(docs, entries, root)))

    existing_dirs = []
    if docs.is_dir():
        existing_dirs = [path for path in docs.rglob("*") if path.is_dir() and not path.is_symlink() and not any(part in SKIP_DIRECTORIES for part in path.parts)]
    planned_indexes: set[Path] = set()
    for directory in sorted(existing_dirs):
        index = directory / "README.md"
        if has_markdown(directory) and not index.exists():
            entries = directory_entries(directory)
            actions.append(RepairAction("create", relative(root, index), "create missing nested documentation index", index_content(directory, entries, root)))
            planned_indexes.add(index)

    if docs_index.is_file():
        updated = append_missing_links(docs_index, root, directory_entries(docs))
        if updated is not None:
            actions.append(RepairAction("update", relative(root, docs_index), "add missing links to the documentation index", updated, docs_index.read_text(encoding="utf-8")))
    for directory in sorted(existing_dirs):
        index = directory / "README.md"
        if index.is_file() and index not in planned_indexes:
            updated = append_missing_links(index, root, directory_entries(directory))
            if updated is not None:
                actions.append(RepairAction("update", relative(root, index), "add missing links to the nested index", updated, index.read_text(encoding="utf-8")))
    if agents.is_file():
        updated = append_agent_link(agents, root)
        if updated is not None:
            actions.append(RepairAction("update", relative(root, agents), "add the documentation index route", updated, agents.read_text(encoding="utf-8")))
    return actions


def apply_repairs(root: Path, actions: list[RepairAction]) -> None:
    root = root.resolve()
    for action in actions:
        path = root / action.path
        if not inside(root, path):
            raise RepairConflict(f"repair target leaves the project root: {action.path}")
        if action.kind == "create":
            if path.exists():
                raise RepairConflict(f"creation target appeared during repair: {action.path}")
        elif action.kind == "update":
            if not path.is_file():
                raise RepairConflict(f"update target disappeared during repair: {action.path}")
            if path.read_text(encoding="utf-8") != action.before:
                raise RepairConflict(f"update target changed during repair: {action.path}")
    for action in actions:
        path = root / action.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(action.content, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview or apply safe documentation structure repairs.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--apply", action="store_true", help="apply only the safe repairs shown by the preview")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        actions = plan_repairs(args.root)
    except (OSError, UnicodeDecodeError, ValueError) as error:
        print(f"r-doc repair: FAIL\n{error}")
        return 1
    if args.json:
        summary = [{"kind": action.kind, "path": action.path, "detail": action.detail} for action in actions]
        print(json.dumps({"apply": args.apply, "actions": summary}, ensure_ascii=False, indent=2))
    elif not actions:
        print("r-doc repair: PASS\nNo safe repairs are pending.")
    else:
        print(f"r-doc repair: {'APPLY' if args.apply else 'PLAN'}")
        for action in actions:
            print(f"{action.kind.upper()} {action.path} - {action.detail}")
    if not actions:
        return 0
    if not args.apply:
        print("No files changed. Review the plan and re-run with --apply after confirmation.")
        return 2
    try:
        apply_repairs(args.root, actions)
    except (OSError, UnicodeDecodeError, RepairConflict) as error:
        print(f"r-doc repair: FAIL\n{error}")
        return 1
    print(f"Applied {len(actions)} safe repair(s). Run audit_docs.py to check remaining semantic findings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
