from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

import grader


RUN_SCHEMA_VERSION = 2
TRACE_SCHEMA_VERSION = 1
HASH_SCHEMA_VERSION = 1
SKILL_CONDITION = "with-r-doc"
OUTPUT_ARTIFACTS = {
    "trace_path": "trace.jsonl",
    "raw_trace_path": "codex-events.jsonl",
    "stderr_path": "codex-stderr.log",
    "final_state_path": "final-state.json",
    "final_response_path": "final-response.md",
}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _safe_component(value: str, label: str) -> str:
    if not value.strip() or value in {".", ".."} or "/" in value or "\\" in value:
        raise ValueError(f"{label} must be a single non-empty path component")
    return value


def _load_task(task_path: Path) -> dict[str, Any]:
    task = _load_json(task_path)
    if task.get("schema_version") != grader.TASK_SCHEMA_VERSION:
        raise ValueError(f"unsupported naturalistic task schema: {task_path}")
    if not isinstance(task.get("task_id"), str) or not task["task_id"].strip():
        raise ValueError(f"task_id is required: {task_path}")
    if not isinstance(task.get("user_prompt"), str) or not task["user_prompt"].strip():
        raise ValueError(f"user_prompt is required: {task_path}")
    fixture_files = task.get("fixture_files")
    if not isinstance(fixture_files, dict) or not fixture_files:
        raise ValueError(f"fixture_files must be a non-empty object: {task_path}")
    snapshot_files = task.get("snapshot_files", task.get("required_files"))
    if not isinstance(snapshot_files, list) or not snapshot_files:
        raise ValueError(f"snapshot_files must be a non-empty list: {task_path}")
    for path in [*fixture_files, *snapshot_files, *task.get("forbidden_reads", [])]:
        if grader._safe_relative(path) is None:
            raise ValueError(f"task contains an unsafe path: {path}")
    for marker in task.get("prompt_forbidden_markers", []):
        if isinstance(marker, str) and marker.casefold() in task["user_prompt"].casefold():
            raise ValueError(f"task prompt discloses a protocol marker: {marker}")
    return task


def _write_fixture(workspace: Path, task: dict[str, Any]) -> dict[str, bytes]:
    initial: dict[str, bytes] = {}
    fixture_files = task["fixture_files"]
    assert isinstance(fixture_files, dict)
    for raw_path, content in fixture_files.items():
        safe_path = grader._safe_relative(raw_path)
        if safe_path is None or not isinstance(content, str):
            raise ValueError(f"fixture file is unsafe or not text: {raw_path}")
        target = workspace / safe_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        initial[safe_path] = target.read_bytes()
    return initial


def _install_skill(project_root: Path, workspace: Path, condition: str) -> None:
    if condition != SKILL_CONDITION:
        return
    source = project_root / "skills" / "r-doc"
    destination = workspace / ".agents" / "skills" / "r-doc"
    if not source.is_dir():
        raise ValueError(f"r-doc source skill is missing: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)


def _workspace_files(workspace: Path, *, excluded: set[str] | None = None) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    excluded = excluded or set()
    for path in workspace.rglob("*"):
        if not path.is_file() or ".agents" in path.parts:
            continue
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(workspace.resolve()).as_posix()
        except ValueError as error:
            raise ValueError(f"workspace file escapes fixture root: {path}") from error
        safe_path = grader._safe_relative(relative)
        if safe_path is None:
            raise ValueError(f"workspace file has an unsafe path: {relative}")
        if safe_path in excluded:
            continue
        files[safe_path] = path.read_bytes()
    return files


def _snapshot(workspace: Path, task: dict[str, Any]) -> dict[str, Any]:
    files: dict[str, str] = {}
    snapshot_files = task.get("snapshot_files", task.get("required_files", []))
    assert isinstance(snapshot_files, list)
    for raw_path in snapshot_files:
        safe_path = grader._safe_relative(raw_path)
        if safe_path is None:
            raise ValueError(f"snapshot path is unsafe: {raw_path}")
        target = workspace / safe_path
        if not target.is_file():
            continue
        try:
            target.resolve().relative_to(workspace.resolve())
        except ValueError as error:
            raise ValueError(f"snapshot path escapes fixture root: {raw_path}") from error
        files[safe_path] = target.read_text(encoding="utf-8")
    return {
        "schema_version": grader.FINAL_STATE_SCHEMA_VERSION,
        "source": grader.NATURALISTIC_FINAL_STATE_PROVENANCE,
        "files": dict(sorted(files.items())),
    }


def _sanitized_text(value: str, workspace: Path, task: dict[str, Any]) -> str:
    sanitized = value.replace(str(workspace), "<fixture-root>")
    sanitized = sanitized.replace(str(workspace).replace("\\", "/"), "<fixture-root>")
    for slash_count in (2, 4, 8):
        sanitized = sanitized.replace(
            str(workspace).replace("\\", "\\" * slash_count),
            "<fixture-root>",
        )
    sanitized = sanitized.replace(str(workspace).replace("\\", "//"), "<fixture-root>")
    fixture_files = task.get("fixture_files", {})
    forbidden = {
        grader._safe_relative(path)
        for path in task.get("forbidden_reads", [])
        if grader._safe_relative(path) is not None
    }
    if isinstance(fixture_files, dict):
        for raw_path, content in fixture_files.items():
            if grader._safe_relative(raw_path) in forbidden and isinstance(content, str) and content:
                sanitized = sanitized.replace(content, "<redacted-fixture-content>")
    return sanitized


def _event_path(value: object, workspace: Path) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.replace("<fixture-root>", str(workspace))
    path = Path(candidate)
    if path.is_absolute():
        try:
            return grader._safe_relative(path.resolve().relative_to(workspace.resolve()).as_posix())
        except ValueError:
            return None
    return grader._safe_relative(candidate)


def _raw_item(event: dict[str, Any]) -> dict[str, Any] | None:
    item = event.get("item")
    if isinstance(item, dict):
        return item
    if event.get("type") in {"command_execution", "file_change", "agent_message"}:
        return event
    return None


def _command_from_item(item: dict[str, Any]) -> tuple[str, int] | None:
    if item.get("type") not in {"command_execution", "command"}:
        return None
    command = item.get("command")
    exit_code = item.get("exit_code")
    if not isinstance(command, str) or not command.strip() or not isinstance(exit_code, int) or isinstance(exit_code, bool):
        return None
    return command, exit_code


def _changed_paths(initial: dict[str, bytes], final: dict[str, bytes]) -> list[str]:
    return sorted(path for path in set(initial) | set(final) if initial.get(path) != final.get(path))


def _shell_tokens(command: str) -> list[str]:
    return [token.casefold().strip("'\"") for token in re.findall(r'''"[^"]*"|'[^']*'|\S+''', command)]


def _is_hidden_path(path: str) -> bool:
    return any(part.startswith(".") and part not in {".", ".."} for part in PurePosixPath(path).parts)


def _read_paths_from_command(
    command: str,
    workspace: Path,
    candidates: set[str],
) -> list[str]:
    lower = command.casefold()
    if re.search(r"\bgit(?:\.exe)?\s+status(?:\s|$)", lower):
        return []
    rg_match = re.search(r"(?<![\w.-])rg(?:\.exe)?(?=\s|$)", lower)
    if rg_match:
        rg_tokens = _shell_tokens(command[rg_match.end() :])
        if "--files" in rg_tokens:
            return []
        includes_hidden = "--hidden" in rg_tokens or "-uu" in rg_tokens or "-uuu" in rg_tokens
        recursive_rg = any(token in {".", "./"} for token in rg_tokens)
        if recursive_rg:
            return sorted(
                path for path in candidates if includes_hidden or not _is_hidden_path(path)
            )
    read_markers = (
        "cat ",
        "type ",
        "get-content",
        " gc ",
        "more ",
        "sed ",
        "head ",
        "tail ",
        "less ",
        "rg ",
        "grep ",
        "select-string",
        "findstr ",
        "pytest",
        "python ",
        "python.exe ",
        "py ",
        "node ",
        "git diff",
        "git show",
    )
    if not any(marker in lower for marker in read_markers):
        return []
    normalized_command = re.sub(r"/+", "/", command.replace("\\", "/")).casefold()
    recursive_read = (
        ("rg " in lower and re.search(r"\s\.\s*(?:[}'\"]|$)", normalized_command) is not None)
        or "get-childitem -recurse" in lower
        or "select-string -path *" in lower
        or "grep -r" in lower
        or "grep -R" in command
    )
    if recursive_read:
        return sorted(candidates)
    paths: list[str] = []
    for candidate in sorted(candidates):
        variants = {
            candidate.replace("\\", "/"),
            str(workspace / candidate).replace("\\", "/"),
        }
        if any(re.sub(r"/+", "/", variant).casefold() in normalized_command for variant in variants):
            paths.append(candidate)
    return paths


def _normalize_trace(
    raw_output: str,
    workspace: Path,
    task: dict[str, Any],
    initial: dict[str, bytes],
    final: dict[str, bytes],
    final_response: str,
) -> list[dict[str, Any]]:
    candidates = {
        grader._safe_relative(path)
        for path in [*task.get("fixture_files", {}), *task.get("snapshot_files", [])]
        if grader._safe_relative(path) is not None
    }
    events: list[dict[str, Any]] = [{"sequence": 0, "event": "prompt", "text": task["user_prompt"]}]
    written_paths: set[str] = set()
    read_paths: set[str] = set()
    try:
        raw_events = [json.loads(line) for line in raw_output.splitlines() if line.strip()]
    except json.JSONDecodeError:
        raw_events = []
    for event in raw_events:
        if not isinstance(event, dict):
            continue
        item = _raw_item(event)
        if item is None:
            continue
        command = _command_from_item(item)
        if command is not None:
            command_text, exit_code = command
            events.append(
                {
                    "sequence": len(events),
                    "event": "command",
                    "name": "command_execution",
                    "command": _sanitized_text(command_text, workspace, task),
                    "exit_code": exit_code,
                }
            )
            read_paths.update(_read_paths_from_command(command_text, workspace, candidates))
        if item.get("type") == "file_change":
            changes = item.get("changes", [])
            if isinstance(changes, list):
                for change in changes:
                    if not isinstance(change, dict):
                        continue
                    changed = _event_path(change.get("path"), workspace)
                    if changed is not None:
                        written_paths.add(changed)
        if item.get("type") == "agent_message":
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                events.append(
                    {
                        "sequence": len(events),
                        "event": "response",
                        "text": _sanitized_text(text, workspace, task),
                    }
                )

    read_paths = sorted(read_paths)
    written_paths.update(_changed_paths(initial, final))
    for path in read_paths:
        events.append({"sequence": len(events), "event": "file_read", "path": path})
    for path in sorted(written_paths):
        events.append({"sequence": len(events), "event": "file_written", "path": path})
    if final_response.strip():
        events.append(
            {
                "sequence": len(events),
                "event": "response",
                "text": _sanitized_text(final_response, workspace, task),
            }
        )
    events.append(
        {
            "sequence": len(events),
            "event": "diff_snapshot",
            "text": "changed_files=" + ",".join(sorted(written_paths)),
        }
    )
    for sequence, event in enumerate(events):
        event["sequence"] = sequence
    return events


def _write_hashes(run_dir: Path, manifest: dict[str, Any]) -> None:
    artifact_paths = {"run.json"}
    for field in OUTPUT_ARTIFACTS:
        artifact_paths.add(str(manifest[field]))
    hashes = {
        path: grader._sha256_lf(run_dir / path)
        for path in sorted(artifact_paths)
    }
    (run_dir / str(manifest["hashes_path"])).write_text(
        json.dumps(
            {"schema_version": HASH_SCHEMA_VERSION, "algorithm": "sha256", "artifacts": hashes},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def capture_run(
    *,
    project_root: Path,
    task_path: Path,
    benchmarks_root: Path,
    profile: str,
    run_id: str,
    condition: str,
    model: str,
    timeout: int,
) -> tuple[Path, dict[str, Any]]:
    profile = _safe_component(profile, "profile")
    run_id = _safe_component(run_id, "run_id")
    if condition not in {"with-r-doc", "baseline-no-r-doc"}:
        raise ValueError(f"unsupported condition: {condition}")
    task_path = task_path.resolve()
    try:
        task_spec_path = task_path.relative_to(project_root).as_posix()
    except ValueError as error:
        raise ValueError("task must be inside the project root") from error
    task = _load_task(task_path)
    task_component = _safe_component(str(task["task_id"]), "task_id")
    run_dir = benchmarks_root / task_component / profile / run_id
    if run_dir.exists():
        raise ValueError(f"benchmark run already exists: {run_dir}")

    with tempfile.TemporaryDirectory(prefix="rdoc-naturalistic-") as directory:
        workspace = Path(directory)
        initial = _write_fixture(workspace, task)
        _install_skill(project_root, workspace, condition)
        final_response_path = workspace / "naturalistic-final-response.md"
        command = [
            "codex",
            "exec",
            "--json",
            "--ephemeral",
            "--ignore-user-config",
            "--skip-git-repo-check",
            "-C",
            str(workspace),
            "-s",
            "danger-full-access",
            "-m",
            model,
            "-o",
            str(final_response_path),
            task["user_prompt"],
        ]
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        final_files = _workspace_files(workspace, excluded={"naturalistic-final-response.md"})
        snapshot = _snapshot(workspace, task)
        raw_final_response = final_response_path.read_text(encoding="utf-8") if final_response_path.is_file() else ""
        final_response = _sanitized_text(raw_final_response, workspace, task)
        normalized_events = _normalize_trace(
            completed.stdout,
            workspace,
            task,
            initial,
            final_files,
            final_response,
        )
        manifest = {
            "schema_version": RUN_SCHEMA_VERSION,
            "profile": profile,
            "run_id": run_id,
            "condition": condition,
            "benchmark_kind": grader.NATURALISTIC_BENCHMARK_KIND,
            "prompt_contract": grader.NATURALISTIC_PROMPT_CONTRACT,
            "activation_ground_truth": grader.NATURALISTIC_ACTIVATION_GROUND_TRUTH,
            "grader_kind": grader.NATURALISTIC_GRADER_KIND,
            "review_provenance": grader.NATURALISTIC_REVIEW_PROVENANCE,
            "capture_source": grader.NATURALISTIC_CAPTURE_SOURCE,
            "final_state_provenance": grader.NATURALISTIC_FINAL_STATE_PROVENANCE,
            "trace_provenance": grader.NATURALISTIC_TRACE_PROVENANCE,
            "task_id": task["task_id"],
            "task_spec_path": task_spec_path,
            "agent": "Codex",
            "model": model,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "source": "codex-cli",
            "agent_exit_code": completed.returncode,
            "trace_path": OUTPUT_ARTIFACTS["trace_path"],
            "raw_trace_path": OUTPUT_ARTIFACTS["raw_trace_path"],
            "stderr_path": OUTPUT_ARTIFACTS["stderr_path"],
            "final_state_path": OUTPUT_ARTIFACTS["final_state_path"],
            "final_response_path": OUTPUT_ARTIFACTS["final_response_path"],
            "hashes_path": "artifact-hashes.json",
        }
        run_dir.mkdir(parents=True)
        (run_dir / "run.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (run_dir / manifest["trace_path"]).write_text(
            "\n".join(json.dumps(event, ensure_ascii=False) for event in normalized_events) + "\n",
            encoding="utf-8",
        )
        (run_dir / manifest["raw_trace_path"]).write_text(
            _sanitized_text(completed.stdout, workspace, task),
            encoding="utf-8",
        )
        (run_dir / manifest["stderr_path"]).write_text(
            _sanitized_text(completed.stderr, workspace, task),
            encoding="utf-8",
        )
        (run_dir / manifest["final_state_path"]).write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (run_dir / manifest["final_response_path"]).write_text(final_response, encoding="utf-8")
        _write_hashes(run_dir, manifest)
        result = grader.grade(task_path, run_dir)
        (run_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return run_dir, result


def main() -> int:
    project_root = Path(__file__).parents[2].resolve()
    parser = argparse.ArgumentParser(description="Capture one naturalistic Codex run with an independent final snapshot.")
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--condition", choices=("with-r-doc", "baseline-no-r-doc"), required=True)
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--root", type=Path, default=project_root / "benchmarks" / "naturalistic-runs")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        run_dir, result = capture_run(
            project_root=project_root,
            task_path=(project_root / args.task).resolve() if not args.task.is_absolute() else args.task.resolve(),
            benchmarks_root=args.root.resolve(),
            profile=args.profile,
            run_id=args.run_id,
            condition=args.condition,
            model=args.model,
            timeout=args.timeout,
        )
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"capture failed: {error}", file=sys.stderr)
        return 1
    print(f"{run_dir} ({result['status']})")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
