from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

from rdoc.markdown import (
    FrontmatterParseError,
    _anchor_slug,
    markdown_anchors,
    parse_frontmatter,
    target_path,
    target_reference,
    validation_targets,
)
from rdoc.security import SECRET_PATTERNS, is_safe_example


def finding(path: Path, message: str) -> str:
    return f"{path.as_posix()} - {message}"


def validate(skill_root: Path) -> list[str]:
    errors: list[str] = []
    skill_root = skill_root.resolve()
    skill_file = skill_root / "SKILL.md"
    if not skill_file.is_file():
        return [finding(skill_file, "missing SKILL.md")]
    text = skill_file.read_text(encoding="utf-8")
    try:
        values, _ = parse_frontmatter(text)
    except FrontmatterParseError as error:
        return [finding(skill_file, f"frontmatter parse failed: {error}")]
    if values.get("name") != skill_root.name:
        errors.append(finding(skill_file, f"frontmatter name must be {skill_root.name!r}"))
    if not values.get("description"):
        errors.append(finding(skill_file, "frontmatter description is required"))
    metadata = values.get("metadata")
    if not isinstance(metadata, dict) or not metadata.get("version"):
        errors.append(finding(skill_file, "metadata.version is required"))
    for markdown_target in validation_targets(text):
        target = target_path(skill_file, markdown_target.raw_target, skill_root)
        if target is not None and not target.exists():
            errors.append(finding(skill_file, f"line {markdown_target.line}: missing linked resource {markdown_target.raw_target}"))
            continue
        reference = target_reference(skill_file, markdown_target.raw_target, skill_root)
        if reference is not None and reference.fragment and target is not None and target.suffix.lower() == ".md":
            anchors = markdown_anchors(target, skill_root, [])
            normalized_fragment = _anchor_slug(reference.fragment)
            normalized_anchors = {anchor.lower() for anchor in anchors}
            if reference.fragment.lower() not in normalized_anchors and normalized_fragment.lower() not in normalized_anchors:
                errors.append(finding(skill_file, f"line {markdown_target.line}: missing linked anchor {markdown_target.raw_target}"))
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
            if any(not is_safe_example(code, match.group(0)) for match in pattern.finditer(content)):
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
