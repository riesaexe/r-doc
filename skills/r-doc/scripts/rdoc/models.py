from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
