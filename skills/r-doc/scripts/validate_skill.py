from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

from audit_docs import LINK_PATTERN, SECRET_PATTERNS, parse_frontmatter, target_path


def finding(path: Path, message: str) -> str:
    return f"{path.as_posix()} - {message}"


def validate(skill_root: Path) -> list[str]:
    errors: list[str] = []
    skill_root = skill_root.resolve()
    skill_file = skill_root / "SKILL.md"
    if not skill_file.is_file():
        return [finding(skill_file, "missing SKILL.md")]
    text = skill_file.read_text(encoding="utf-8")
    values, _ = parse_frontmatter(text)
    if values.get("name") != skill_root.name:
        errors.append(finding(skill_file, f"frontmatter name must be {skill_root.name!r}"))
    if not values.get("description"):
        errors.append(finding(skill_file, "frontmatter description is required"))
    if not values.get("metadata.version") and "metadata:" not in text:
        errors.append(finding(skill_file, "metadata.version is required"))
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in LINK_PATTERN.finditer(line):
            target = target_path(skill_file, match.group(1), skill_root)
            if target is not None and not target.exists():
                errors.append(finding(skill_file, f"line {line_number}: missing linked resource {match.group(1)}"))
    ui_file = skill_root / "agents" / "openai.yaml"
    if not ui_file.is_file():
        errors.append(finding(ui_file, "missing OpenAI UI metadata"))
    else:
        ui_text = ui_file.read_text(encoding="utf-8")
        for field in ("display_name:", "short_description:", "default_prompt:"):
            if field not in ui_text:
                errors.append(finding(ui_file, f"missing UI field {field}"))
        for icon_line in re.findall(r"^\s*icon_(?:small|large):\s*[\"']?([^\"'\s]+)", ui_text, flags=re.MULTILINE):
            icon_reference = icon_line[2:] if icon_line.startswith("./") else icon_line
            if not (skill_root / icon_reference).resolve().is_file():
                errors.append(finding(ui_file, f"missing icon resource {icon_line}"))
    for path in skill_root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if re.search(r"(?:[A-Za-z]:[\\/]|/)(?:Users|home)[\\/]", content, flags=re.IGNORECASE):
            errors.append(finding(path, "contains a machine-specific user path"))
        for pattern, code in SECRET_PATTERNS:
            if pattern.search(content):
                errors.append(finding(path, f"contains a possible sensitive value ({code})"))
    for script in (skill_root / "scripts").glob("*.py"):
        try:
            ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
        except (OSError, SyntaxError) as error:
            errors.append(finding(script, f"Python syntax check failed: {error}"))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the r-doc skill package.")
    parser.add_argument("skill_root", type=Path)
    args = parser.parse_args()
    errors = validate(args.skill_root)
    if errors:
        print("skill package: FAIL")
        print("\n".join(errors))
        return 1
    print("skill package: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
