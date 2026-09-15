from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import SimpleNamespace
from typing import Any


RUN_SCHEMA_VERSION = 2
FINAL_STATE_SCHEMA_VERSION = 2
HASH_SCHEMA_VERSION = 1
TASK_SCHEMA_VERSION = 2
RESULT_SCHEMA_VERSION = 2
NATURALISTIC_BENCHMARK_KIND = "naturalistic-effectiveness"
NATURALISTIC_PROMPT_CONTRACT = "naturalistic-user-task"
NATURALISTIC_ACTIVATION_GROUND_TRUTH = "independent-task-spec"
NATURALISTIC_GRADER_KIND = "independent-grader"
NATURALISTIC_REVIEW_PROVENANCE = "independent-grader"
NATURALISTIC_CAPTURE_SOURCE = "naturalistic-capture-runner"
NATURALISTIC_FINAL_STATE_PROVENANCE = "runner-generated-from-workspace"
NATURALISTIC_TRACE_PROVENANCE = "runner-normalized-raw-cli"
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
    if "\x00" in normalized:
        return None
    posix = PurePosixPath(normalized)
    windows = PureWindowsPath(normalized)
    if (
        posix.is_absolute()
        or windows.is_absolute()
        or windows.drive
        or "." in posix.parts
        or ".." in posix.parts
        or posix.as_posix() != normalized
    ):
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_errors(manifest: dict[str, Any], run_dir: Path) -> list[str]:
    hashes_value = _safe_relative(manifest.get("hashes_path"))
    errors: list[str] = []
    if hashes_value is None:
        return ["run.json is missing a safe hashes_path"]
    hashes_path = run_dir / hashes_value
    if not hashes_path.is_file():
        return [f"missing benchmark artifact: {hashes_value}"]
    try:
        hashes = _load_json(hashes_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return [f"invalid artifact hash manifest: {error}"]
    if hashes.get("schema_version") != HASH_SCHEMA_VERSION or hashes.get("algorithm") != "sha256":
        errors.append("artifact hash manifest has an unsupported schema or algorithm")
    artifacts = hashes.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        return errors + ["artifact hash manifest must contain a non-empty artifacts object"]
    required_paths = {
        "run.json",
        str(manifest.get("trace_path", "")),
        str(manifest.get("final_state_path", "")),
        str(manifest.get("final_response_path", "")),
        str(manifest.get("raw_trace_path", "")),
    }
    if not required_paths.issubset(artifacts):
        missing = sorted(path for path in required_paths if path not in artifacts)
        errors.append("artifact hash manifest is missing: " + ", ".join(missing))
    for raw_path, expected in artifacts.items():
        safe_path = _safe_relative(raw_path)
        if safe_path is None or safe_path != raw_path:
            errors.append(f"artifact hash path is unsafe: {raw_path}")
            continue
        if not isinstance(expected, str) or len(expected) != 64:
            errors.append(f"artifact hash is invalid: {raw_path}")
            continue
        artifact_path = run_dir / safe_path
        if not artifact_path.is_file():
            errors.append(f"hashed artifact is missing: {raw_path}")
            continue
        if _sha256(artifact_path) != expected:
            errors.append(f"artifact hash mismatch: {raw_path}")
    return errors


def _materialize_argument(value: object) -> object:
    if isinstance(value, dict):
        return SimpleNamespace(**{str(key): _materialize_argument(item) for key, item in value.items()})
    if isinstance(value, list):
        return [_materialize_argument(item) for item in value]
    return value


def _load_callable(root: Path, module_path: str, callable_name: str) -> Any:
    module_file = root / module_path
    if not module_file.is_file():
        raise ValueError(f"callable module is missing: {module_path}")
    module_name = f"naturalistic_fixture_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, module_file)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load callable module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(root))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    value = getattr(module, callable_name, None)
    if not callable(value):
        raise ValueError(f"callable is missing: {module_path}:{callable_name}")
    return value


def _contains_key(value: object, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_key(item, key) for item in value)
    return False


def _run_executable_checks(task: dict[str, Any], files: dict[str, str]) -> list[dict[str, str]]:
    checks = task.get("executable_checks", [])
    if not isinstance(checks, list) or not checks:
        return [{"id": "executable_checks", "status": "fail", "details": "task has no executable checks"}]

    results: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="rdoc-naturalistic-grade-") as directory:
        workspace = Path(directory)
        for path, content in files.items():
            safe_path = _safe_relative(path)
            if safe_path != path or not isinstance(content, str):
                results.append(
                    {
                        "id": "snapshot",
                        "status": "fail",
                        "details": f"final snapshot contains an unsafe or non-text file: {path}",
                    }
                )
                continue
            target = workspace / safe_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        existing_python_path = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = (
            str(workspace)
            if not existing_python_path
            else str(workspace) + os.pathsep + existing_python_path
        )
        for check in checks:
            if not isinstance(check, dict):
                results.append({"id": "unknown", "status": "fail", "details": "executable check is not an object"})
                continue
            check_id = str(check.get("id", "unknown"))
            kind = check.get("kind")
            try:
                if kind == "pytest":
                    paths = check.get("paths", [])
                    if not isinstance(paths, list) or not paths:
                        raise ValueError("pytest check requires paths")
                    safe_paths = [_safe_relative(path) for path in paths]
                    if any(path is None for path in safe_paths):
                        raise ValueError("pytest check contains an unsafe path")
                    completed = subprocess.run(
                        [sys.executable, "-m", "pytest", "-q", *[str(path) for path in safe_paths]],
                        cwd=workspace,
                        env=environment,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=60,
                        check=False,
                    )
                    if completed.returncode != 0:
                        raise ValueError(f"pytest exited with {completed.returncode}")
                elif kind in {"callable_return", "callable_attribute", "callable_raises"}:
                    module_path = _safe_relative(check.get("module_path"))
                    callable_name = check.get("callable")
                    if module_path is None or not isinstance(callable_name, str) or not callable_name.strip():
                        raise ValueError("callable check requires a safe module_path and callable")
                    function = _load_callable(workspace, module_path, callable_name)
                    args = [_materialize_argument(value) for value in check.get("args", [])]
                    kwargs = {
                        str(key): _materialize_argument(value)
                        for key, value in check.get("kwargs", {}).items()
                    }
                    raised = False
                    try:
                        with contextlib.redirect_stderr(io.StringIO()):
                            returned = function(*args, **kwargs)
                    except BaseException as error:
                        if kind == "callable_raises" and error.__class__.__name__ == check.get("exception"):
                            raised = True
                            returned = None
                        else:
                            raise ValueError(f"callable raised {error.__class__.__name__}: {error}") from error
                    if kind == "callable_return":
                        if returned != check.get("expected_return"):
                            raise ValueError("callable returned an unexpected value")
                        for forbidden_key in check.get("forbidden_keys", []):
                            if isinstance(forbidden_key, str) and _contains_key(returned, forbidden_key):
                                raise ValueError(f"callable return still contains {forbidden_key!r}")
                    elif kind == "callable_attribute":
                        attribute = check.get("attribute")
                        if not isinstance(attribute, str) or not hasattr(returned, attribute):
                            raise ValueError(f"callable result has no attribute {attribute!r}")
                        if getattr(returned, attribute) != check.get("expected"):
                            raise ValueError(f"callable attribute {attribute!r} has an unexpected value")
                    elif kind == "callable_raises" and not raised:
                        raise ValueError(f"callable did not raise {check.get('exception')!r}")
                elif kind == "text_assertions":
                    path = _safe_relative(check.get("path"))
                    if path is None or path not in files:
                        raise ValueError("text assertion path is missing or unsafe")
                    content = files[path]
                    for expected in check.get("contains", []):
                        if expected not in content:
                            raise ValueError(f"text does not contain {expected!r}")
                    for forbidden in check.get("not_contains", []):
                        if forbidden in content:
                            raise ValueError(f"text still contains {forbidden!r}")
                else:
                    raise ValueError(f"unsupported executable check kind: {kind}")
            except (OSError, RuntimeError, TypeError, ValueError, subprocess.TimeoutExpired) as error:
                results.append({"id": check_id, "status": "fail", "details": str(error)})
            else:
                results.append({"id": check_id, "status": "pass", "details": f"{kind} check passed"})
    return results


def grade(task_path: Path, run_dir: Path) -> dict[str, Any]:
    task = _load_json(task_path)
    manifest = _load_json(run_dir / "run.json")
    errors: list[str] = []
    checks: list[dict[str, str]] = []

    if task.get("schema_version") != TASK_SCHEMA_VERSION:
        errors.append("task specification has an unsupported schema_version")

    manifest_ok = (
        manifest.get("schema_version") == RUN_SCHEMA_VERSION
        and manifest.get("benchmark_kind") == NATURALISTIC_BENCHMARK_KIND
        and manifest.get("prompt_contract") == NATURALISTIC_PROMPT_CONTRACT
        and manifest.get("activation_ground_truth") == NATURALISTIC_ACTIVATION_GROUND_TRUTH
        and manifest.get("grader_kind") == NATURALISTIC_GRADER_KIND
        and manifest.get("review_provenance") == NATURALISTIC_REVIEW_PROVENANCE
        and manifest.get("capture_source") == NATURALISTIC_CAPTURE_SOURCE
        and manifest.get("final_state_provenance") == NATURALISTIC_FINAL_STATE_PROVENANCE
        and manifest.get("trace_provenance") == NATURALISTIC_TRACE_PROVENANCE
        and manifest.get("task_id") == task.get("task_id")
        and manifest.get("condition") in {"with-r-doc", "baseline-no-r-doc"}
        and manifest.get("agent_exit_code") == 0
    )
    checks.append(_check(manifest_ok, "manifest", "naturalistic manifest identifies an independent-grader run"))
    if not manifest_ok:
        errors.append("run.json does not identify a naturalistic independent-grader run")
    if manifest.get("agent_exit_code") != 0:
        errors.append("agent process did not exit successfully")

    artifact_errors = _artifact_errors(manifest, run_dir)
    errors.extend(artifact_errors)
    checks.append(_check(not artifact_errors, "artifact_integrity", "runner artifacts match their recorded SHA-256 hashes"))

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
                if final_state.get("schema_version") != FINAL_STATE_SCHEMA_VERSION:
                    outcome_errors.append("final-state.json has an unsupported schema_version")
                if final_state.get("source") != NATURALISTIC_FINAL_STATE_PROVENANCE:
                    outcome_errors.append("final-state.json is not marked as a runner workspace snapshot")
                for raw_path, content in raw_files.items():
                    safe_path = _safe_relative(raw_path)
                    if safe_path != raw_path or not isinstance(content, str):
                        outcome_errors.append(f"final-state.json contains an unsafe or non-text file: {raw_path}")
                        continue
                    files[safe_path] = content
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
            safe_path = _safe_relative(path)
            content = files.get(safe_path) if safe_path is not None else None
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

    executable_results = _run_executable_checks(task, {path: content for path, content in files.items()})
    executable_errors = [
        f"{item['id']}: {item['details']}"
        for item in executable_results
        if item.get("status") != "pass"
    ]
    errors.extend(executable_errors)
    checks.append(_check(not executable_errors, "executable_outcome", "grader-owned tests and behavior checks pass on the final snapshot"))

    response_ok = final_response_path.is_file() and bool(final_response_path.read_text(encoding="utf-8").strip())
    checks.append(_check(response_ok, "final_response", "final response artifact is present for audit only"))
    if not response_ok:
        errors.append("final response artifact is missing or empty")

    return _result(task, manifest, checks, errors, executable_results)


def _result(
    task: dict[str, Any],
    manifest: dict[str, Any],
    checks: list[dict[str, str]],
    errors: list[str],
    executable_results: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    status = "pass" if not errors else "fail"
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
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
            "executable_outcome": 100.0 if next((item for item in checks if item["id"] == "executable_outcome"), {}).get("status") == "pass" else 0.0,
            "context_safety": 100.0 if next((item for item in checks if item["id"] == "forbidden_reads"), {}).get("status") == "pass" else 0.0,
            "trace_integrity": 100.0 if next((item for item in checks if item["id"] == "trace_integrity"), {}).get("status") == "pass" else 0.0,
        },
        "agent_review_used": False,
        "executable_checks": executable_results or [],
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
