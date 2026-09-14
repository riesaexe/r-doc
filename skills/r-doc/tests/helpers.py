from pathlib import Path


def write_file(root: Path, relative_path: str, content: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def topic(identifier: str, title: str = "Guide") -> str:
    return "\n".join(
        [
            "---",
            f"id: {identifier}",
            "type: guide",
            "status: active",
            f"title: {title}",
            "created: 2026-09-14",
            "updated: 2026-09-14",
            "---",
            "",
            f"# {title}",
        ]
    )


def valid_project(root: Path) -> None:
    write_file(root, "AGENTS.md", "# Entry\n\n[Docs](docs/README.md)\n")
    write_file(root, "docs/README.md", "# Docs\n\n[Guide](guide/README.md)\n\n[Entry](../AGENTS.md)\n")
    write_file(root, "docs/guide/README.md", "# Guide\n\n[Topic](doc.md)\n\n[Docs](../README.md)\n")
    write_file(root, "docs/guide/doc.md", topic("DOC-001"))
