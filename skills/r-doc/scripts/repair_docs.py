from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from audit_docs import ProjectConfig, canonical_path, load_project_config, navigation_targets, path_is_excluded, target_path


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
    return canonical_path(root, path) is not None


def has_markdown(directory: Path, root: Path, config: ProjectConfig) -> bool:
    if not directory.is_dir():
        return False
    for path in directory.rglob("*.md"):
        if not path_is_excluded(root, path, config):
            return True
    return False


def markdown_direct_children(directory: Path, root: Path, config: ProjectConfig) -> list[Path]:
    return sorted(path for path in directory.glob("*.md") if path.name != "README.md" and not path_is_excluded(root, path, config))


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


def directory_entries(directory: Path, root: Path, config: ProjectConfig) -> list[tuple[str, str]]:
    entries = [(document_label(path), path.name) for path in markdown_direct_children(directory, root, config)]
    for child in sorted(path for path in directory.iterdir() if path.is_dir() and not path.is_symlink() and not path_is_excluded(root, path, config)):
        if has_markdown(child, root, config):
            label = document_label(child / "README.md") if (child / "README.md").is_file() else child.name.replace("-", " ").replace("_", " ").title()
            entries.append((label, f"{child.name}/README.md"))
    return entries


def relative_link(source_directory: Path, target: Path) -> str:
    return os.path.relpath(target, source_directory).replace(os.sep, "/")


def index_content(directory: Path, entries: list[tuple[str, str]], root: Path, docs: Path) -> str:
    if directory == docs:
        title = "Documentation index"
        parent_link = relative_link(directory, root / "AGENTS.md")
        parent_label = "Project entrypoint"
    else:
        title = f"{directory.name.replace('-', ' ').replace('_', ' ').title()} documentation index"
        parent_link = relative_link(directory, directory.parent / "README.md")
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


def agent_content(docs_root: str) -> str:
    docs_index = f"{docs_root.strip('/')}/README.md"
    return "\n".join(
        [
            "# Project documentation entrypoint",
            "",
            "This is a generated navigation skeleton. Complete project-specific commands, rules, and routes after reviewing the repository.",
            "",
            "## Quick start",
            "",
            "1. Read this file;",
            f"2. Read [{docs_index}]({docs_index});",
            "3. Follow the relevant topic index;",
            "4. Run the project's validation and test commands before declaring work complete.",
            "",
            "## Context-loading order",
            "",
            "```text",
            "AGENTS.md",
            f"→ {docs_index}",
            "→ relevant topic README.md",
            "→ target document",
            "```",
            "",
            "## Documentation index",
            "",
            f"Start with [{docs_index}]({docs_index}). Keep detailed project knowledge in {docs_root}/.",
            "",
        ]
    )


def linked_targets_from_text(text: str, path: Path, root: Path) -> set[Path]:
    targets: set[Path] = set()
    for markdown_target in navigation_targets(text):
        target = target_path(path, markdown_target.raw_target, root)
        if target is not None:
            canonical = canonical_path(root, target)
            if canonical is not None:
                targets.add(canonical)
    return targets


def linked_targets(path: Path, root: Path) -> set[Path]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    return linked_targets_from_text(text, path, root)


def update_index(path: Path, root: Path, entries: list[tuple[str, str]], parent_target: Path, parent_label: str) -> str | None:
    before = path.read_text(encoding="utf-8")
    content = before.rstrip()
    linked = linked_targets_from_text(content, path, root)
    missing = []
    for label, target in entries:
        canonical = canonical_path(root, path.parent / target)
        if canonical is not None and canonical not in linked:
            missing.append((label, target))
    if missing:
        lines = [content, ""]
        if "## Document links" not in content:
            lines.extend(["## Document links", ""])
        lines.extend(f"- [{label}]({target})" for label, target in missing)
        lines.append("")
        content = "\n".join(lines)

    parent_link = relative_link(path.parent, parent_target)
    parent_canonical = canonical_path(root, parent_target)
    parent_missing = parent_canonical is not None and parent_canonical not in linked
    if not missing and not parent_missing:
        return None
    if parent_missing:
        lines = [content.rstrip(), ""]
        if f"## {parent_label}" not in content:
            lines.extend([f"## {parent_label}", ""])
        lines.extend([f"[{parent_label}]({parent_link})", ""])
        content = "\n".join(lines)
    if content == before:
        return None

    return content


def update_agent(path: Path, root: Path, docs_index: Path) -> str | None:
    before = path.read_text(encoding="utf-8")
    target = canonical_path(root, docs_index)
    if target is None or target in linked_targets(path, root):
        return None
    link = relative_link(path.parent, docs_index)
    lines = [before.rstrip(), ""]
    if "## Documentation index" not in before:
        lines.extend(["## Documentation index", ""])
    lines.extend([f"[Documentation index]({link})", ""])
    return "\n".join(lines)


def plan_repairs(root: Path) -> list[RepairAction]:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"project root does not exist: {root}")
    config, config_problems = load_project_config(root)
    if config_problems:
        details = "; ".join(problem.message for problem in config_problems)
        raise ValueError(f"project configuration is invalid: {details}")
    agents = root / "AGENTS.md"
    docs = config.docs_path(root)
    docs_index = docs / "README.md"
    if not inside(root, docs):
        raise ValueError(f"configured documentation root leaves the project root: {config.docs_root}")
    actions: list[RepairAction] = []
    if not agents.exists():
        actions.append(RepairAction("create", relative(root, agents), "create missing project entrypoint", agent_content(config.docs_root)))
    if not docs_index.exists():
        entries = directory_entries(docs, root, config) if docs.is_dir() else []
        actions.append(RepairAction("create", relative(root, docs_index), "create missing documentation index", index_content(docs, entries, root, docs)))

    existing_dirs = []
    if docs.is_dir():
        existing_dirs = [path for path in docs.rglob("*") if path.is_dir() and not path.is_symlink() and not path_is_excluded(root, path, config)]
    planned_indexes: set[Path] = set()
    for directory in sorted(existing_dirs):
        index = directory / "README.md"
        if has_markdown(directory, root, config) and not index.exists():
            entries = directory_entries(directory, root, config)
            actions.append(RepairAction("create", relative(root, index), "create missing nested documentation index", index_content(directory, entries, root, docs)))
            planned_indexes.add(index)

    if docs_index.is_file():
        updated = update_index(docs_index, root, directory_entries(docs, root, config), root / "AGENTS.md", "Project entrypoint")
        if updated is not None:
            actions.append(RepairAction("update", relative(root, docs_index), "complete the documentation index routes", updated, docs_index.read_text(encoding="utf-8")))
    for directory in sorted(existing_dirs):
        index = directory / "README.md"
        if index.is_file() and index not in planned_indexes:
            updated = update_index(index, root, directory_entries(directory, root, config), directory.parent / "README.md", "Parent index")
            if updated is not None:
                actions.append(RepairAction("update", relative(root, index), "complete the nested index routes", updated, index.read_text(encoding="utf-8")))
    if agents.is_file():
        updated = update_agent(agents, root, docs_index)
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
