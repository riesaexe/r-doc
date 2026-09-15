from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

from rdoc.security import SECRET_PATTERNS, is_safe_example
from evaluate_agent import evaluate, load_cases


RUN_SCHEMA_VERSION = 2
SUMMARY_SCHEMA_VERSION = 4
TRACE_SCHEMA_VERSION = 2
RUN_CONDITIONS = {"with-r-doc", "baseline-no-r-doc"}
BENCHMARK_KINDS = {"skill-layer-ablation", "naturalistic-effectiveness"}
PROMPT_CONTRACTS = {"fixed-protocol", "naturalistic-user-task"}
GRADER_KINDS = {"agent-self-review", "independent-grader"}
ACTIVATION_GROUND_TRUTHS = {"case-contract", "independent-task-spec"}
REVIEW_PROVENANCE = {"agent-generated", "independent-grader"}
CONFORMANCE_METADATA = {
    "benchmark_kind": "skill-layer-ablation",
    "benchmark_name": "Conformance Benchmark",
    "prompt_contract": "fixed-protocol",
    "activation_ground_truth": "case-contract",
    "grader_kind": "agent-self-review",
    "review_provenance": "agent-generated",
}
TRACE_EVENTS = {
    "trace_start",
    "scenario_start",
    "prompt",
    "activation_decision",
    "skill_selected",
    "path_checked",
    "file_read",
    "command",
    "file_written",
    "governance_report",
    "final_response",
    "diff_snapshot",
    "review",
    "scenario_end",
    "trace_end",
}
TRACE_HEADER_FIELDS = {"run_id", "profile", "condition", "agent", "model", "skill_version"}
TRACE_COMMON_FIELDS = {"schema_version", "sequence", "event"}
TRACE_EVENT_FIELDS = {
    "trace_start": TRACE_COMMON_FIELDS | TRACE_HEADER_FIELDS,
    "scenario_start": TRACE_COMMON_FIELDS | {"scenario_id"},
    "prompt": TRACE_COMMON_FIELDS | {"scenario_id", "text"},
    "activation_decision": TRACE_COMMON_FIELDS | {"scenario_id", "decision"},
    "skill_selected": TRACE_COMMON_FIELDS | {"scenario_id", "skill"},
    "path_checked": TRACE_COMMON_FIELDS | {"scenario_id", "path"},
    "file_read": TRACE_COMMON_FIELDS | {"scenario_id", "path"},
    "command": TRACE_COMMON_FIELDS | {"scenario_id", "name", "command", "exit_code"},
    "file_written": TRACE_COMMON_FIELDS | {"scenario_id", "path"},
    "governance_report": TRACE_COMMON_FIELDS | {"scenario_id", "text"},
    "final_response": TRACE_COMMON_FIELDS | {"scenario_id", "text"},
    "diff_snapshot": TRACE_COMMON_FIELDS | {"scenario_id", "text"},
    "review": TRACE_COMMON_FIELDS | {"scenario_id", "dimension", "status", "basis"},
    "scenario_end": TRACE_COMMON_FIELDS | {"scenario_id"},
    "trace_end": TRACE_COMMON_FIELDS,
}
TRACE_REQUIRED_FIELDS = {
    "trace_start": TRACE_COMMON_FIELDS | TRACE_HEADER_FIELDS,
    "scenario_start": TRACE_COMMON_FIELDS | {"scenario_id"},
    "prompt": TRACE_COMMON_FIELDS | {"scenario_id", "text"},
    "activation_decision": TRACE_COMMON_FIELDS | {"scenario_id", "decision"},
    "skill_selected": TRACE_COMMON_FIELDS | {"scenario_id", "skill"},
    "path_checked": TRACE_COMMON_FIELDS | {"scenario_id", "path"},
    "file_read": TRACE_COMMON_FIELDS | {"scenario_id", "path"},
    "command": TRACE_COMMON_FIELDS | {"scenario_id", "exit_code"},
    "file_written": TRACE_COMMON_FIELDS | {"scenario_id", "path"},
    "governance_report": TRACE_COMMON_FIELDS | {"scenario_id", "text"},
    "final_response": TRACE_COMMON_FIELDS | {"scenario_id", "text"},
    "diff_snapshot": TRACE_COMMON_FIELDS | {"scenario_id", "text"},
    "review": TRACE_COMMON_FIELDS | {"scenario_id", "dimension", "status", "basis"},
    "scenario_end": TRACE_COMMON_FIELDS | {"scenario_id"},
    "trace_end": TRACE_COMMON_FIELDS,
}
METRIC_NAMES = (
    "activation_accuracy",
    "audit_compliance",
    "unnecessary_reads",
    "forbidden_reads",
    "required_reads_missing",
    "task_success",
)
REQUIRED_MANIFEST_FIELDS = (
    "schema_version",
    "profile",
    "run_id",
    "condition",
    "benchmark_kind",
    "prompt_contract",
    "activation_ground_truth",
    "grader_kind",
    "review_provenance",
    "agent",
    "model",
    "skill_version",
    "captured_at",
    "source",
    "trace_path",
)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _non_empty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _trace_file_path(manifest: dict[str, Any], run_dir: Path) -> tuple[Path | None, list[str]]:
    trace_path = manifest.get("trace_path")
    if not isinstance(trace_path, str) or not trace_path.strip():
        return None, [f"{run_dir}: run.json trace_path must be non-empty"]

    trace = (run_dir / trace_path).resolve()
    try:
        trace.relative_to(run_dir.resolve())
    except ValueError:
        return None, [f"{run_dir}: trace_path leaves the run directory"]
    if not trace.is_file():
        return None, [f"{run_dir}: trace_path does not exist: {trace_path}"]
    return trace, []


def _validate_manifest(
    manifest: dict[str, Any],
    run_dir: Path,
    profile: str,
    run_id: str,
    expected_skill_version: str,
) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_MANIFEST_FIELDS:
        if field not in manifest:
            errors.append(f"{run_dir}: run.json is missing {field}")
    if manifest.get("schema_version") != RUN_SCHEMA_VERSION:
        errors.append(f"{run_dir}: unsupported run.json schema_version")
    if manifest.get("profile") != profile or manifest.get("run_id") != run_id:
        errors.append(f"{run_dir}: run.json identity does not match its directory")
    if manifest.get("condition") not in RUN_CONDITIONS:
        errors.append(f"{run_dir}: condition must be with-r-doc or baseline-no-r-doc")
    if manifest.get("benchmark_kind") not in BENCHMARK_KINDS:
        errors.append(f"{run_dir}: benchmark_kind is unsupported")
    if manifest.get("prompt_contract") not in PROMPT_CONTRACTS:
        errors.append(f"{run_dir}: prompt_contract is unsupported")
    if manifest.get("activation_ground_truth") not in ACTIVATION_GROUND_TRUTHS:
        errors.append(f"{run_dir}: activation_ground_truth is unsupported")
    if manifest.get("grader_kind") not in GRADER_KINDS:
        errors.append(f"{run_dir}: grader_kind is unsupported")
    if manifest.get("review_provenance") not in REVIEW_PROVENANCE:
        errors.append(f"{run_dir}: review_provenance is unsupported")
    if manifest.get("benchmark_kind") == "skill-layer-ablation":
        for field, expected in CONFORMANCE_METADATA.items():
            if field == "benchmark_name":
                continue
            if manifest.get(field) != expected:
                errors.append(f"{run_dir}: {field} must be {expected!r} for skill-layer-ablation")
    for field in ("agent", "model", "captured_at", "source"):
        if not _non_empty(manifest.get(field)):
            errors.append(f"{run_dir}: run.json {field} must be non-empty")
    if manifest.get("skill_version") != expected_skill_version:
        errors.append(f"{run_dir}: run.json skill_version must match cases")

    _, trace_errors = _trace_file_path(manifest, run_dir)
    errors.extend(trace_errors)
    return errors


def _load_trace(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}: trace line {line_number} is not valid JSON") from error
        if not isinstance(value, dict):
            raise ValueError(f"{path}: trace line {line_number} must be a JSON object")
        events.append(value)
    if not events:
        raise ValueError(f"{path}: trace must contain at least a trace_start and trace_end event")
    return events


def _trace_command_label(value: dict[str, Any]) -> str:
    return " ".join(
        item.strip()
        for key in ("name", "command")
        for item in [value.get(key)]
        if isinstance(item, str) and item.strip()
    ).strip()


def _evidence_command_signature(value: object) -> tuple[str, int] | None:
    if not isinstance(value, dict):
        return None
    label = _trace_command_label(value)
    exit_code = value.get("exit_code")
    if not label or not isinstance(exit_code, int) or isinstance(exit_code, bool):
        return None
    return label.casefold(), exit_code


def _trace_contains_secret(events: list[dict[str, Any]]) -> bool:
    serialized = json.dumps(events, ensure_ascii=False)
    for pattern, code in SECRET_PATTERNS:
        for match in pattern.finditer(serialized):
            if not is_safe_example(code, match.group(0)):
                return True
    return False


def _validate_trace(
    events: list[dict[str, Any]],
    trace_path: Path,
    manifest: dict[str, Any],
    evidence: dict[str, Any],
    cases: dict[str, Any],
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    expected_ids = {
        str(case["id"])
        for case in cases.get("scenarios", [])
        if isinstance(case, dict) and _non_empty(case.get("id"))
    }
    derived: dict[str, dict[str, Any]] = {
        identifier: {
            "activation": None,
            "skill_selected": None,
            "prompt": None,
            "paths_checked": [],
            "files_read": [],
            "files_written": [],
            "commands": [],
            "governance_report": None,
            "final_response": None,
            "final_diff": None,
            "review": {},
        }
        for identifier in expected_ids
    }

    if events[0].get("event") != "trace_start":
        errors.append(f"{trace_path}: first event must be trace_start")
    if events[-1].get("event") != "trace_end":
        errors.append(f"{trace_path}: last event must be trace_end")

    header_fields = ("run_id", "profile", "condition", "agent", "model", "skill_version")
    active_scenario: str | None = None
    started: set[str] = set()
    ended: set[str] = set()
    for expected_sequence, event in enumerate(events):
        if event.get("schema_version") != TRACE_SCHEMA_VERSION:
            errors.append(f"{trace_path}: trace event {expected_sequence} has unsupported schema_version")
        if event.get("sequence") != expected_sequence:
            errors.append(f"{trace_path}: trace event {expected_sequence} has invalid sequence")

        event_name = event.get("event")
        if event_name not in TRACE_EVENTS:
            errors.append(f"{trace_path}: trace event {expected_sequence} has unsupported event type: {event_name}")
            continue
        allowed_fields = TRACE_EVENT_FIELDS[event_name]
        required_fields = TRACE_REQUIRED_FIELDS[event_name]
        unknown_fields = sorted(set(event) - allowed_fields)
        if unknown_fields:
            errors.append(
                f"{trace_path}: {event_name} event {expected_sequence} has unsupported fields: "
                + ", ".join(unknown_fields)
            )
        missing_fields = sorted(required_fields - set(event))
        if missing_fields:
            errors.append(
                f"{trace_path}: {event_name} event {expected_sequence} is missing fields: "
                + ", ".join(missing_fields)
            )
        if event_name == "trace_start":
            for field in header_fields:
                if event.get(field) != manifest.get(field):
                    errors.append(f"{trace_path}: trace_start {field} does not match run.json")
            if expected_sequence != 0:
                errors.append(f"{trace_path}: trace_start must be the first event")
            continue
        if event_name == "trace_end":
            if expected_sequence != len(events) - 1:
                errors.append(f"{trace_path}: trace_end must be the last event")
            if active_scenario is not None:
                errors.append(f"{trace_path}: trace_end occurred before scenario_end: {active_scenario}")
            continue

        scenario_id = event.get("scenario_id")
        if not _non_empty(scenario_id):
            errors.append(f"{trace_path}: {event_name} event {expected_sequence} requires scenario_id")
            continue
        scenario_id = str(scenario_id)
        if scenario_id not in expected_ids:
            errors.append(f"{trace_path}: trace references unknown scenario: {scenario_id}")

        if event_name == "scenario_start":
            if active_scenario is not None:
                errors.append(f"{trace_path}: scenario_start nested inside {active_scenario}")
            if scenario_id in started:
                errors.append(f"{trace_path}: scenario started more than once: {scenario_id}")
            started.add(scenario_id)
            active_scenario = scenario_id
            continue
        if event_name == "scenario_end":
            if active_scenario != scenario_id:
                errors.append(f"{trace_path}: scenario_end does not match active scenario: {scenario_id}")
            ended.add(scenario_id)
            active_scenario = None
            continue

        if active_scenario != scenario_id:
            errors.append(f"{trace_path}: {event_name} is outside its active scenario: {scenario_id}")
        if event_name in {"path_checked", "file_read", "file_written"}:
            path_value = event.get("path")
            if not _non_empty(path_value):
                errors.append(f"{trace_path}: {event_name} event {expected_sequence} requires a non-empty path")
                continue
            if scenario_id in derived:
                field = {
                    "path_checked": "paths_checked",
                    "file_read": "files_read",
                    "file_written": "files_written",
                }[event_name]
                derived[scenario_id][field].append(str(path_value))
        elif event_name == "command":
            if not _trace_command_label(event):
                errors.append(f"{trace_path}: command event {expected_sequence} requires name or command")
            exit_code = event.get("exit_code")
            if not isinstance(exit_code, int) or isinstance(exit_code, bool):
                errors.append(f"{trace_path}: command event {expected_sequence} requires an integer exit_code")
            elif scenario_id in derived:
                derived[scenario_id]["commands"].append(
                    {
                        key: event[key]
                    for key in ("name", "command", "exit_code")
                    if key in event
                    }
                )
        elif event_name in {"prompt", "governance_report", "final_response", "diff_snapshot"}:
            text = event.get("text")
            if not _non_empty(text):
                errors.append(f"{trace_path}: {event_name} event {expected_sequence} requires non-empty text")
            elif scenario_id in derived:
                field = {
                    "prompt": "prompt",
                    "governance_report": "governance_report",
                    "final_response": "final_response",
                    "diff_snapshot": "final_diff",
                }[event_name]
                if derived[scenario_id][field] is not None:
                    errors.append(f"{trace_path}: {scenario_id} has duplicate {event_name} events")
                else:
                    derived[scenario_id][field] = text
        elif event_name == "activation_decision":
            decision = event.get("decision")
            if decision not in {"activated", "declined"}:
                errors.append(
                    f"{trace_path}: activation_decision event {expected_sequence} has invalid decision"
                )
            elif scenario_id in derived:
                if derived[scenario_id]["activation"] is not None:
                    errors.append(f"{trace_path}: {scenario_id} has duplicate activation_decision events")
                else:
                    derived[scenario_id]["activation"] = decision
        elif event_name == "skill_selected":
            skill = event.get("skill")
            if not _non_empty(skill):
                errors.append(f"{trace_path}: skill_selected event {expected_sequence} requires a non-empty skill")
            elif scenario_id in derived:
                if derived[scenario_id]["skill_selected"] is not None:
                    errors.append(f"{trace_path}: {scenario_id} has duplicate skill_selected events")
                else:
                    derived[scenario_id]["skill_selected"] = skill
        elif event_name == "review":
            dimension = event.get("dimension")
            status = event.get("status")
            basis = event.get("basis")
            if not _non_empty(dimension) or status not in {"pass", "partial", "fail"} or not _non_empty(basis):
                errors.append(f"{trace_path}: review event {expected_sequence} is invalid")
            elif scenario_id in derived:
                review = derived[scenario_id]["review"]
                if dimension in review:
                    errors.append(f"{trace_path}: {scenario_id} has duplicate review dimension: {dimension}")
                else:
                    review[dimension] = {"status": status, "basis": basis}

    if active_scenario is not None:
        errors.append(f"{trace_path}: scenario is missing scenario_end: {active_scenario}")
    for identifier in sorted(expected_ids - started):
        errors.append(f"{trace_path}: scenario_start is missing: {identifier}")
    for identifier in sorted(expected_ids - ended):
        errors.append(f"{trace_path}: scenario_end is missing: {identifier}")
    if started != expected_ids:
        errors.append(f"{trace_path}: trace scenario coverage does not match cases")
    if ended != expected_ids:
        errors.append(f"{trace_path}: trace scenario completion does not match cases")
    if _trace_contains_secret(events):
        errors.append(f"{trace_path}: trace contains a possible sensitive value")

    expected_review_dimensions = {
        str(dimension)
        for dimension in cases.get("review_dimensions", [])
        if _non_empty(dimension)
    }
    condition_skill = {"with-r-doc": "r-doc", "baseline-no-r-doc": "none"}.get(manifest.get("condition"))
    expected_activation_by_id = {
        str(case.get("id")): case.get("expected_activation")
        for case in cases.get("scenarios", [])
        if isinstance(case, dict) and _non_empty(case.get("id"))
    }
    for identifier in sorted(expected_ids):
        scenario = derived[identifier]
        for field in (
            "prompt",
            "activation",
            "skill_selected",
            "governance_report",
            "final_response",
            "final_diff",
        ):
            if scenario[field] is None:
                errors.append(f"{trace_path}: {identifier} is missing trace-derived field: {field}")
        expected_skill = (
            condition_skill
            if expected_activation_by_id.get(identifier) == "activated"
            else "none"
        )
        if expected_skill is not None and scenario["skill_selected"] != expected_skill:
            errors.append(
                f"{trace_path}: {identifier} skill_selected must be {expected_skill!r} for condition "
                f"{manifest.get('condition')!r}"
            )
        if set(scenario["review"]) != expected_review_dimensions:
            errors.append(f"{trace_path}: {identifier} review dimensions do not match cases")

    evidence_by_id = {
        str(item.get("id")): item
        for item in evidence.get("scenarios", [])
        if isinstance(item, dict) and _non_empty(item.get("id"))
    }
    for identifier in sorted(expected_ids):
        item = evidence_by_id.get(identifier)
        if not isinstance(item, dict):
            continue
        for field in (
            "activation",
            "skill_selected",
            "prompt",
            "governance_report",
            "final_response",
            "final_diff",
        ):
            if item.get(field) != derived[identifier][field]:
                errors.append(f"{trace_path}: trace/evidence mismatch for {identifier} {field}")
        for field in ("paths_checked", "files_read", "files_written"):
            evidence_values = item.get(field)
            if not isinstance(evidence_values, list) or not all(isinstance(value, str) for value in evidence_values):
                continue
            trace_values = derived[identifier][field]
            if set(evidence_values) != set(trace_values):
                errors.append(f"{trace_path}: trace/evidence mismatch for {identifier} {field}")
        evidence_commands = item.get("commands")
        if isinstance(evidence_commands, list):
            evidence_signature = [
                signature
                for command in evidence_commands
                for signature in [_evidence_command_signature(command)]
                if signature is not None
            ]
            trace_signature = [
                signature
                for command in derived[identifier]["commands"]
                for signature in [_evidence_command_signature(command)]
                if signature is not None
            ]
            if evidence_signature != trace_signature or len(evidence_signature) != len(evidence_commands):
                errors.append(f"{trace_path}: trace/evidence mismatch for {identifier} commands")
        evidence_review = item.get("review")
        if evidence_review != derived[identifier]["review"]:
            errors.append(f"{trace_path}: trace/evidence mismatch for {identifier} review")

    return errors, {
        "event_count": len(events),
        "scenario_count": len(started),
        "derived": derived,
    }


def _scenario_metrics(
    result: dict[str, Any],
    evidence: dict[str, Any],
    cases: dict[str, Any],
) -> dict[str, float | int]:
    evidence_by_id = {
        item.get("id"): item
        for item in evidence.get("scenarios", [])
        if isinstance(item, dict) and _non_empty(item.get("id"))
    }
    result_scenarios = result.get("scenarios", [])
    count = len(result_scenarios)
    if count == 0:
        return {
            "activation_accuracy": 0.0,
            "audit_compliance": 0.0,
            "unnecessary_reads": 0,
            "forbidden_reads": 0,
            "required_reads_missing": 0,
            "task_success": 0.0,
        }

    activation_passes = 0
    audit_passes = 0
    task_passes = 0
    unnecessary_reads = 0
    forbidden_reads = 0
    required_reads_missing = 0
    read_policies = {
        case["id"]: {
            "required": set(case.get("required_files_read", [])),
            "allowed": set(case.get("allowed_files_read", case.get("required_files_read", []))),
            "forbidden": set(case.get("forbidden_files_read", [])),
        }
        for case in cases.get("scenarios", [])
        if isinstance(case, dict) and _non_empty(case.get("id"))
    }
    for scenario in result_scenarios:
        if not isinstance(scenario, dict):
            continue
        machine_checks = scenario.get("machine_checks", {})
        if machine_checks.get("activation_boundary") == "pass":
            activation_passes += 1
        if machine_checks.get("deterministic_verification") == "pass":
            audit_passes += 1
        if scenario.get("status") == "pass":
            task_passes += 1
        identifier = scenario.get("id")
        item = evidence_by_id.get(identifier, {})
        reads = item.get("files_read", []) if isinstance(item, dict) else []
        if isinstance(reads, list):
            read_set = {read for read in reads if isinstance(read, str)}
            policy = read_policies.get(
                identifier,
                {"required": set(), "allowed": set(), "forbidden": set()},
            )
            unnecessary_reads += len(read_set - policy["allowed"])
            forbidden_reads += len(read_set & policy["forbidden"])
            required_reads_missing += len(policy["required"] - read_set)

    return {
        "activation_accuracy": round(activation_passes / count * 100, 2),
        "audit_compliance": round(audit_passes / count * 100, 2),
        "unnecessary_reads": unnecessary_reads,
        "forbidden_reads": forbidden_reads,
        "required_reads_missing": required_reads_missing,
        "task_success": round(task_passes / count * 100, 2),
    }


def _metric_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        return {"run_count": 0}
    metrics = [item["metrics"] for item in items]
    summary: dict[str, Any] = {"run_count": len(items)}
    for metric in METRIC_NAMES:
        raw_values = [item.get(metric, 0.0) for item in metrics]
        values = [float(value) for value in raw_values]
        suffix = "average" if metric in {"unnecessary_reads", "forbidden_reads", "required_reads_missing"} else ""
        key = f"{metric}_{suffix}" if suffix else metric
        summary[key] = round(statistics.mean(values), 2)
        if metric in {"unnecessary_reads", "forbidden_reads", "required_reads_missing"}:
            summary[f"{metric}_total"] = sum(raw_values)
    return summary


def _validated_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        record
        for record in records
        if record.get("manifest_validation") == "pass"
        and record.get("trace_validation") == "pass"
        and record.get("status") in {"pass", "partial"}
    ]


def _profile_summary(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    records = _validated_records(records)
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for record in records:
        profile = str(record["profile"])
        condition = str(record["condition"])
        grouped.setdefault(profile, {}).setdefault(condition, []).append(record)

    summaries: dict[str, dict[str, Any]] = {}
    for profile, by_condition in grouped.items():
        condition_summaries = {
            condition: _metric_summary(items)
            for condition, items in sorted(by_condition.items())
        }
        summary: dict[str, Any] = {
            "run_count": sum(len(items) for items in by_condition.values()),
            "conditions": condition_summaries,
        }
        if len(condition_summaries) == 1:
            summary.update(next(iter(condition_summaries.values())))
        summaries[profile] = summary
    return summaries


T_CRITICAL_95 = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    11: 2.201,
    12: 2.179,
    13: 2.160,
    14: 2.145,
    15: 2.131,
    16: 2.120,
    17: 2.110,
    18: 2.101,
    19: 2.093,
    20: 2.086,
    21: 2.080,
    22: 2.074,
    23: 2.069,
    24: 2.064,
    25: 2.060,
    26: 2.056,
    27: 2.052,
    28: 2.048,
    29: 2.045,
    30: 2.042,
}


def _delta_statistics(values: list[float]) -> dict[str, float | None | str]:
    count = len(values)
    mean = statistics.mean(values)
    stdev = statistics.stdev(values) if count > 1 else 0.0
    if count > 1:
        critical = T_CRITICAL_95.get(count - 1, 1.96)
        half_width = critical * stdev / math.sqrt(count)
        ci95_low: float | None = round(mean - half_width, 2)
        ci95_high: float | None = round(mean + half_width, 2)
        ci95_method = "student-t-95"
    else:
        ci95_low = None
        ci95_high = None
        ci95_method = "unavailable-below-two-pairs"
    return {
        "mean": round(statistics.mean(values), 2),
        "median": round(statistics.median(values), 2),
        "stdev": round(stdev, 2),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "ci95_low": ci95_low,
        "ci95_high": ci95_high,
        "ci95_method": ci95_method,
    }


def _paired_comparisons(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = _validated_records(records)
    grouped: dict[tuple[str, str], dict[str, dict[str, list[dict[str, Any]]]]] = {}
    for record in records:
        condition = record.get("condition")
        if condition not in RUN_CONDITIONS:
            continue
        key = (str(record.get("agent")), str(record.get("model")))
        run_id = str(record.get("run_id"))
        grouped.setdefault(key, {}).setdefault(condition, {}).setdefault(run_id, []).append(record)

    comparisons: list[dict[str, Any]] = []
    for (agent, model), by_condition in sorted(grouped.items()):
        with_runs = by_condition.get("with-r-doc", {})
        baseline_runs = by_condition.get("baseline-no-r-doc", {})
        paired_ids = sorted(
            run_id
            for run_id in set(with_runs) & set(baseline_runs)
            if len(with_runs[run_id]) == 1 and len(baseline_runs[run_id]) == 1
        )
        paired_with = [with_runs[run_id][0] for run_id in paired_ids]
        paired_baseline = [baseline_runs[run_id][0] for run_id in paired_ids]
        condition_items = {
            "with-r-doc": _metric_summary(paired_with),
            "baseline-no-r-doc": _metric_summary(paired_baseline),
        }
        per_run_deltas: list[dict[str, Any]] = []
        delta_values: dict[str, list[float]] = {metric: [] for metric in METRIC_NAMES}
        for run_id, with_record, baseline_record in zip(paired_ids, paired_with, paired_baseline):
            run_metrics: dict[str, float] = {}
            for metric in METRIC_NAMES:
                delta = float(with_record["metrics"].get(metric, 0.0)) - float(baseline_record["metrics"].get(metric, 0.0))
                delta_values[metric].append(delta)
                run_metrics[metric] = round(delta, 2)
            per_run_deltas.append({"run_id": run_id, "delta": run_metrics})

        comparison: dict[str, Any] = {
            "agent": agent,
            "model": model,
            "paired_run_count": len(paired_ids),
            "paired_run_ids": paired_ids,
            "unpaired_run_counts": {
                "with-r-doc": len(with_runs) - len(paired_ids),
                "baseline-no-r-doc": len(baseline_runs) - len(paired_ids),
            },
            "trend_readiness": len(paired_ids) >= 3,
            "statistical_readiness": len(paired_ids) >= 5,
            "strong_evidence_readiness": len(paired_ids) >= 10,
            "sample_size_guidance": {
                "trend_min_pairs": 3,
                "statistical_min_pairs": 5,
                "strong_evidence_min_pairs": 10,
            },
            "conditions": condition_items,
            "delta": {
                metric: round(statistics.mean(values), 2) if values else None
                for metric, values in delta_values.items()
            },
            "delta_statistics": {
                metric: _delta_statistics(values)
                for metric, values in delta_values.items()
                if values
            },
            "per_run_deltas": per_run_deltas,
        }
        comparisons.append(comparison)
    return comparisons


def aggregate(cases: dict[str, Any], benchmarks_root: Path) -> tuple[dict[str, Any], list[tuple[Path, dict[str, Any]]]]:
    records: list[dict[str, Any]] = []
    result_files: list[tuple[Path, dict[str, Any]]] = []
    errors: list[str] = []
    if not benchmarks_root.is_dir():
        return (
            {
                "schema_version": SUMMARY_SCHEMA_VERSION,
                "evaluation_skill_version": cases.get("skill_version"),
                **CONFORMANCE_METADATA,
                "metric_semantics": {
                    "activation_accuracy": "Activation protocol compliance against the disclosed case contract; not natural activation accuracy.",
                    "task_success": "Machine checks plus agent-generated review; not independently graded task success.",
                },
                "status": "pending",
                "profiles": {},
                "paired_comparisons": [],
                "runs": [],
                "errors": [],
                "notes": "No real agent benchmark runs have been captured yet.",
            },
            [],
        )

    evidence_files = sorted(benchmarks_root.glob("*/run-*/evidence.json"))
    for evidence_path in evidence_files:
        run_dir = evidence_path.parent
        profile = run_dir.parent.name
        run_id = run_dir.name
        manifest_path = run_dir / "run.json"
        if not manifest_path.is_file():
            errors.append(f"{run_dir}: run.json is required for a real benchmark run")
            continue
        try:
            manifest = _load_json(manifest_path)
            evidence = _load_json(evidence_path)
            if manifest.get("benchmark_kind") != CONFORMANCE_METADATA["benchmark_kind"]:
                errors.append(
                    f"{run_dir}: conformance aggregator rejects non-conformance benchmark_kind "
                    f"{manifest.get('benchmark_kind')!r}"
                )
                continue
            manifest_errors = _validate_manifest(
                manifest,
                run_dir,
                profile,
                run_id,
                str(cases.get("skill_version", "")),
            )
            errors.extend(manifest_errors)
            result = evaluate(cases, evidence, enforce_forbidden_reads=True)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"{run_dir}: {error}")
            continue

        trace_path, trace_path_errors = _trace_file_path(manifest, run_dir)
        trace_events: list[dict[str, Any]] | None = None
        trace_derived: dict[str, Any] = {}
        trace_errors = list(trace_path_errors)
        if trace_path is not None:
            try:
                trace_events = _load_trace(trace_path)
                trace_validation_errors, trace_details = _validate_trace(
                    trace_events,
                    trace_path,
                    manifest,
                    evidence,
                    cases,
                )
                trace_errors.extend(trace_validation_errors)
                trace_derived = trace_details.get("derived", {})
            except (OSError, ValueError, json.JSONDecodeError) as error:
                trace_errors.append(f"{run_dir}: {error}")
        errors.extend(error for error in trace_errors if error not in errors)

        metrics = _scenario_metrics(result, evidence, cases)
        records.append(
            {
                "profile": profile,
                "run_id": run_id,
                "condition": manifest.get("condition"),
                "benchmark_kind": manifest.get("benchmark_kind"),
                "prompt_contract": manifest.get("prompt_contract"),
                "activation_ground_truth": manifest.get("activation_ground_truth"),
                "grader_kind": manifest.get("grader_kind"),
                "review_provenance": manifest.get("review_provenance"),
                "agent": manifest.get("agent"),
                "model": manifest.get("model"),
                "captured_at": manifest.get("captured_at"),
                "status": result.get("status"),
                "percentage": result.get("percentage", 0.0),
                "metrics": metrics,
                "evidence_path": str(evidence_path.as_posix()),
                "trace_path": str((run_dir / str(manifest.get("trace_path", ""))).as_posix()),
                "manifest_validation": "pass" if not manifest_errors else "fail",
                "trace_event_count": len(trace_events) if trace_events is not None else 0,
                "trace_validation": "pass" if trace_events is not None and not trace_errors else "fail",
                "trace_derived": trace_derived,
            }
        )
        result_files.append((run_dir / "result.json", result))

    if not records:
        status = "pending" if not errors else "fail"
    elif errors or any(record["status"] == "fail" for record in records):
        status = "fail"
    elif any(record["status"] == "partial" for record in records):
        status = "partial"
    else:
        status = "pass"

    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "evaluation_skill_version": cases.get("skill_version"),
        **CONFORMANCE_METADATA,
        "metric_semantics": {
            "activation_accuracy": "Activation protocol compliance against the disclosed case contract; not natural activation accuracy.",
            "task_success": "Machine checks plus agent-generated review; not independently graded task success.",
        },
        "status": status,
        "profiles": _profile_summary(records),
        "paired_comparisons": _paired_comparisons(records),
        "runs": records,
        "errors": errors,
        "notes": (
            "No real agent benchmark runs have been captured yet."
            if not records and not errors
            else (
                "This is a skill-layer ablation: the fixed protocol discloses scenario activation, reads, and commands, while the baseline keeps the same deterministic helpers but omits r-doc Skill instructions. "
                "Metrics are derived from real captured evidence and structurally validated traces. "
                "unnecessary_reads counts unique files outside each case's allowed read set; "
                "forbidden_reads counts unique files in its forbidden set. task_success includes agent-generated review and is not an independent effectiveness score."
            )
        ),
    }
    return summary, result_files


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    project_root = Path(__file__).parents[3]
    parser = argparse.ArgumentParser(description="Aggregate validated r-doc agent benchmark runs.")
    parser.add_argument("--root", type=Path, default=project_root / "benchmarks")
    parser.add_argument("--cases", type=Path, default=project_root / "skills" / "r-doc" / "evals" / "cases.json")
    parser.add_argument("--output", type=Path, help="write summary JSON to this path")
    parser.add_argument("--write-results", action="store_true", help="write each derived result.json beside its evidence")
    parser.add_argument("--strict", action="store_true", help="fail unless real runs exist and all runs pass")
    args = parser.parse_args()

    try:
        cases = load_cases(args.cases)
        summary, result_files = aggregate(cases, args.root)
        if args.write_results:
            for path, result in result_files:
                path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        output = args.output or args.root / "summary.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR {error}", file=sys.stderr)
        return 1

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.strict and summary["status"] != "pass":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
