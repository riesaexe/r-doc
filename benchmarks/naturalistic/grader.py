from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


RUN_SCHEMA_VERSION = 1
TRACE_EVENTS = {"prompt", "file_read", "file_written", "command", "response", "diff_snapshot", "review"}
TRACE_FIELDS = {
    "prompt": {"sequence", "event", "text"},
    "file_read": {"sequence", "event", "path"},
    "file_written": {"sequence", "event", "path"},
    "command": {"sequence", "event", "name", "command", "exit_code"},
    "response": {"sequence", "event", "text"},
    "diff_snapshot": {"sequence", "event", "text"},
    "review": {"sequence", "event", "dimension", "status", "basis"},
}
PROMPT_REQUIRED_FIELDS = {"sequence", "event", "text"}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _safe_relative(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.replace("\\", "/")
    posix = PurePosixPath(normalized)
    windows = PureWindowsPath(normalized)
    if posix.is_absolute() or windows.is_absolute() or windows.drive or ".." in posix.parts:
        return None
    return posix.as_posix()


def _check(condition: bool, check_id: str, details: str) -> dict[str, str]:
    return {"id": check_id, "status": "pass" if condition else "fail", "details": details}


def _load_trace(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"trace line {line_number} is not valid JSON")
            continue
        if not isinstance(event, dict):
            errors.append(f"trace line {line_number} is not an object")
            continue
        event_type = event.get("event")
        if event_type not in TRACE_EVENTS:
            errors.append(f"trace line {line_number} has unsupported event {event_type!r}")
            continue
        unsupported = sorted(set(event) - TRACE_FIELDS[event_type])
        missing = sorted(TRACE_FIELDS[event_type] - set(event))
        if unsupported:
            errors.append(f"trace line {line_number} has unsupported fields: {', '.join(unsupported)}")
        if missing:
            errors.append(f"trace line {line_number} is missing fields: {', '.join(missing)}")
        if event_type in {"file_read", "file_written"} and _safe_relative(event.get("path")) is None:
            errors.append(f"trace line {line_number} has an unsafe path")
        events.append(event)
    sequences = [event.get("sequence") for event in events]
    if sequences != list(range(len(events))):
        errors.append("trace sequence must be contiguous from zero")
    return events, errors


def _prompt_errors(task: dict[str, Any], events: list[dict[str, Any]]) -> list[str]:
    expected = task.get("user_prompt")
    prompts = [event for event in events if event.get("event") == "prompt"]
    errors: list[str] = []
    if len(prompts) != 1:
        errors.append("trace must contain exactly one prompt event")
        return errors
    if prompts[0].get("text") != expected:
        errors.append("trace prompt does not match the task prompt")
    for marker in task.get("prompt_forbidden_markers", []):
        if not isinstance(marker, str):
            continue
        if marker.casefold() in str(expected).casefold():
            errors.append(f"task prompt discloses a protocol marker: {marker}")
    return errors


def grade(task_path: Path, run_dir: Path) -> dict[str, Any]:
    task = _load_json(task_path)
    manifest = _load_json(run_dir / "run.json")
    errors: list[str] = []
    checks: list[dict[str, str]] = []

    manifest_ok = (
        manifest.get("schema_version") == RUN_SCHEMA_VERSION
        and manifest.get("benchmark_kind") == "naturalistic-effectiveness"
        and manifest.get("prompt_contract") == "naturalistic-user-task"
        and manifest.get("activation_ground_truth") == "independent-task-spec"
        and manifest.get("grader_kind") == "independent-grader"
        and manifest.get("review_provenance") == "independent-grader"
        and manifest.get("task_id") == task.get("task_id")
        and manifest.get("condition") in {"with-r-doc", "baseline-no-r-doc"}
    )
    checks.append(_check(manifest_ok, "manifest", "naturalistic manifest identifies an independent-grader run"))
    if not manifest_ok:
        errors.append("run.json does not identify a naturalistic independent-grader run")

    trace_path_value = _safe_relative(manifest.get("trace_path"))
    final_state_value = _safe_relative(manifest.get("final_state_path"))
    final_response_value = _safe_relative(manifest.get("final_response_path"))
    path_ok = all((trace_path_value, final_state_value, final_response_value))
    checks.append(_check(path_ok, "artifact_paths", "trace, final-state, and final-response paths stay relative to the run"))
    if not path_ok:
        errors.append("run.json contains missing or unsafe artifact paths")
        return _result(task, manifest, checks, errors)

    trace_path = run_dir / str(trace_path_value)
    final_state_path = run_dir / str(final_state_value)
    final_response_path = run_dir / str(final_response_value)
    for path in (trace_path, final_state_path, final_response_path):
        if not path.is_file():
            errors.append(f"missing benchmark artifact: {path.name}")

    events: list[dict[str, Any]] = []
    trace_errors: list[str] = []
    if trace_path.is_file():
        events, trace_errors = _load_trace(trace_path)
    errors.extend(trace_errors)
    checks.append(_check(not trace_errors, "trace_integrity", "normalized trace is valid and contiguous"))

    prompt_errors = _prompt_errors(task, events) if events else ["trace has no usable events"]
    errors.extend(prompt_errors)
    checks.append(_check(not prompt_errors, "prompt_contract", "prompt contains only the naturalistic user task"))

    forbidden = {_safe_relative(path) for path in task.get("forbidden_reads", [])}
    reads = {
        _safe_relative(event.get("path"))
        for event in events
        if event.get("event") == "file_read"
    }
    forbidden_hits = sorted(path for path in reads & forbidden if path is not None)
    if forbidden_hits:
        errors.append("forbidden reads: " + ", ".join(forbidden_hits))
    checks.append(_check(not forbidden_hits, "forbidden_reads", "trace did not read forbidden fixture paths"))

    outcome_errors: list[str] = []
    files: dict[str, Any] = {}
    if final_state_path.is_file():
        try:
            final_state = _load_json(final_state_path)
            raw_files = final_state.get("files")
            if not isinstance(raw_files, dict):
                outcome_errors.append("final-state.json files must be an object")
            else:
                files = raw_files
        except (OSError, ValueError, json.JSONDecodeError) as error:
            outcome_errors.append(str(error))
    required_files = task.get("required_files", [])
    for path in required_files:
        safe_path = _safe_relative(path)
        if safe_path is None or safe_path not in files:
            outcome_errors.append(f"required final file is missing: {path}")
    assertions = task.get("assertions", {})
    if isinstance(assertions, dict):
        for path, rules in assertions.items():
            content = files.get(path)
            if not isinstance(content, str) or not isinstance(rules, dict):
                outcome_errors.append(f"cannot grade assertions for {path}")
                continue
            for expected in rules.get("contains", []):
                if expected not in content:
                    outcome_errors.append(f"{path} does not contain {expected!r}")
            for forbidden_text in rules.get("not_contains", []):
                if forbidden_text in content:
                    outcome_errors.append(f"{path} still contains {forbidden_text!r}")
    errors.extend(outcome_errors)
    checks.append(_check(not outcome_errors, "final_state_outcome", "independent assertions pass on the final repository snapshot"))

    response_ok = final_response_path.is_file() and bool(final_response_path.read_text(encoding="utf-8").strip())
    checks.append(_check(response_ok, "final_response", "final response artifact is present for audit only"))
    if not response_ok:
        errors.append("final response artifact is missing or empty")

    return _result(task, manifest, checks, errors)


def _result(task: dict[str, Any], manifest: dict[str, Any], checks: list[dict[str, str]], errors: list[str]) -> dict[str, Any]:
    status = "pass" if not errors else "fail"
    return {
        "schema_version": 1,
        "status": status,
        "benchmark_kind": "naturalistic-effectiveness",
        "grader_kind": "independent-grader",
        "task_id": task.get("task_id"),
        "condition": manifest.get("condition"),
        "agent": manifest.get("agent"),
        "model": manifest.get("model"),
        "metrics": {
            "task_success": 100.0 if status == "pass" else 0.0,
            "outcome_compliance": 100.0 if next((item for item in checks if item["id"] == "final_state_outcome"), {}).get("status") == "pass" else 0.0,
            "context_safety": 100.0 if next((item for item in checks if item["id"] == "forbidden_reads"), {}).get("status") == "pass" else 0.0,
            "trace_integrity": 100.0 if next((item for item in checks if item["id"] == "trace_integrity"), {}).get("status") == "pass" else 0.0,
        },
        "agent_review_used": False,
        "checks": checks,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Independently grade a naturalistic r-doc benchmark run.")
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = grade(args.task.resolve(), args.run_dir.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"naturalistic grader: {result['status'].upper()}")
        for check in result["checks"]:
            print(f"{check['status'].upper()} {check['id']} - {check['details']}")
        for error in result["errors"]:
            print(f"ERROR {error}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
