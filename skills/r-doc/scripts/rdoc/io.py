from __future__ import annotations

from pathlib import Path

from .config import relative
from .models import Finding, FindingList


def add(finding_list: list[Finding], severity: str, code: str, root: Path, path: Path, message: str, line: int | None = None) -> None:
    finding = Finding(severity, code, relative(root, path), message, line)
    if isinstance(finding_list, FindingList):
        if finding in finding_list._seen:
            return
        finding_list._seen.add(finding)
    elif finding in finding_list:
        return
    finding_list.append(finding)


def read_text(path: Path, root: Path, findings: list[Finding]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        add(findings, "error", "encoding", root, path, f"not valid UTF-8: {error}")
    except OSError as error:
        add(findings, "error", "read-error", root, path, str(error))
    return ""
