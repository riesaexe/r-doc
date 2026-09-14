from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

import yaml

from .io import read_text
from .models import Finding, FrontmatterParseError, MarkdownTarget, TargetReference


REFERENCE_DEFINITION_PATTERN = re.compile(
    r"(?im)^[ \t]{0,3}\[([^\]]+)\]:[ \t]*(?:<([^>\n]+)>|(\S+))"
)
REFERENCE_LINK_PATTERN = re.compile(r"(?<!\!)!?\[([^\]\n]+)\]\[([^\]\n]*)\]")


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
            targets.append((match.start(), MarkdownTarget(raw_target, line, is_image=text[match.start()] == "!", definition_key=key)))

    for match in re.finditer(r"(?<!\!)!?\[([^\]\n]+)\]", lexical_text):
        after = lexical_text[match.end()] if match.end() < len(lexical_text) else ""
        before = text[match.start() - 1] if match.start() else ""
        if after in '([:"':
            continue
        if before in "](" or any(start <= match.start() < end for start, end in definition_spans):
            continue
        key = " ".join(match.group(1).split()).casefold()
        raw_target = definitions.get(key)
        if raw_target:
            line = text.count("\n", 0, match.start()) + 1
            targets.append((match.start(), MarkdownTarget(raw_target, line, is_image=text[match.start()] == "!", definition_key=key)))

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


def _is_emoji_character(character: str) -> bool:
    codepoint = ord(character)
    return (
        0x1F000 <= codepoint <= 0x1FAFF
        or 0x2300 <= codepoint <= 0x23FF
        or 0x2600 <= codepoint <= 0x27BF
        or 0x2B00 <= codepoint <= 0x2BFF
    )


def _anchor_slug(value: str) -> str:
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = re.sub(r"<[^>]+>", "", value)
    value = value.lower()
    value = "".join(
        character
        for character in value
        if character.isalnum()
        or character in " -_"
        or _is_emoji_character(character)
        or character in "\ufe0e\ufe0f\u200d"
    )
    return value.replace(" ", "-")


def markdown_anchors(path: Path, root: Path, findings: list[Finding]) -> set[str]:
    text = read_text(path, root, findings)
    lexical_lines = mask_markdown_non_link_regions(text).splitlines()
    original_lines = text.splitlines()
    anchors: set[str] = set()
    counts: dict[str, int] = {}

    def register_heading(value: str) -> None:
        slug = _anchor_slug(value)
        if not slug:
            return
        index = counts.get(slug, 0)
        counts[slug] = index + 1
        anchors.add(slug if index == 0 else f"{slug}-{index}")

    try:
        _, frontmatter_end = parse_frontmatter(text)
    except FrontmatterParseError:
        frontmatter_end = 0
    for index, (line, lexical_line) in enumerate(zip(original_lines, lexical_lines)):
        if index < frontmatter_end or not lexical_line.strip():
            continue
        lexical_match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", lexical_line)
        original_match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        if lexical_match and original_match:
            register_heading(original_match.group(1))
            continue
        if index + 1 >= len(lexical_lines) or not line.strip():
            continue
        if re.match(r"^\s{0,3}(?:=+|-+)\s*$", lexical_lines[index + 1]):
            register_heading(line.strip())

    anchor_pattern = re.compile(
        r"<a\b[^>]*?\b(?:id|name)\s*=\s*(?:\"([^\"]+)\"|'([^']+)'|([^\s>]+))[^>]*>",
        flags=re.IGNORECASE,
    )
    lexical_text = mask_markdown_non_link_regions(text)
    for match in anchor_pattern.finditer(lexical_text):
        value = next(group for group in match.groups() if group is not None)
        anchors.add(value)
    return anchors
