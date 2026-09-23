from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

import yaml

from .models import ConfigProblem
from .security import SECRET_CODES


SKIP_DIRECTORIES = {".git", ".venv", "node_modules", "dist", "build", "coverage"}
CONFIG_PATHS = (Path(".r-doc.yaml"), Path("docs/r-doc.yaml"), Path("r-doc.yaml"))
CONFIG_KEYS = {
    "version",
    "project_type",
    "governance_level",
    "docs_root",
    "required_document_types",
    "exclude",
    "gates",
    "relationships",
    "sensitive_allowlist",
    "decision_notes",
}
GATE_VALUES = {"advisory", "audit", "blocking"}
GOVERNANCE_LEVELS = {"minimal", "standard", "strict"}


@dataclass(frozen=True)
class ProjectConfig:
    docs_root: str = "docs"
    decision_notes_root: str = ".agents/notes"
    decision_notes_required: bool = False
    exclude: tuple[str, ...] = ()
    required_document_types: tuple[str, ...] = ()
    gates: dict[str, str] | None = None
    relationships: dict[str, tuple[str, ...]] | None = None
    sensitive_allowlist: dict[str, tuple[str, ...]] | None = None
    source: Path | None = None
    governance_level: str = "standard"

    def docs_path(self, root: Path) -> Path:
        return root / self.docs_root

    def decision_notes_path(self, root: Path) -> Path:
        return root / self.decision_notes_root

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
    governance_level = "standard"
    raw_governance_level = values.get("governance_level", governance_level)
    if not isinstance(raw_governance_level, str) or raw_governance_level not in GOVERNANCE_LEVELS:
        problems.append(
            _config_error(
                source,
                "config-governance-level",
                f"governance_level must be one of: {', '.join(sorted(GOVERNANCE_LEVELS))}",
            )
        )
    else:
        governance_level = raw_governance_level
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

    decision_notes_root = ".agents/notes"
    decision_notes_required = False
    if "decision_notes" in values:
        raw_decision_notes = values["decision_notes"]
        if not isinstance(raw_decision_notes, dict):
            problems.append(_config_error(source, "config-decision-notes", "decision_notes must be a mapping with an optional root"))
        else:
            unknown_decision_notes = sorted(str(key) for key in raw_decision_notes if key != "root")
            if unknown_decision_notes:
                problems.append(_config_error(source, "config-decision-notes", f"unsupported decision_notes field(s): {', '.join(unknown_decision_notes)}"))
            raw_notes_root = raw_decision_notes.get("root", decision_notes_root)
            if not isinstance(raw_notes_root, str) or not raw_notes_root.strip():
                problems.append(_config_error(source, "config-decision-notes", "decision_notes.root must be a non-empty relative path"))
            else:
                normalized_notes_root = raw_notes_root.strip().replace("\\", "/")
                notes_root_path = PurePosixPath(normalized_notes_root)
                if (
                    notes_root_path.is_absolute()
                    or PureWindowsPath(normalized_notes_root).is_absolute()
                    or ".." in notes_root_path.parts
                    or normalized_notes_root in {"", "."}
                ):
                    problems.append(_config_error(source, "config-decision-notes", "decision_notes.root must stay inside the project root"))
                else:
                    decision_notes_root = normalized_notes_root.strip("/")
                    decision_notes_required = True

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
        governance_level=governance_level,
        docs_root=docs_root,
        decision_notes_root=decision_notes_root,
        decision_notes_required=decision_notes_required,
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
