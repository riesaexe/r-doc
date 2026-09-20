from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

import aggregate
import capture_codex
import export_public_evidence
import grader


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _raw_item(event: dict[str, Any]) -> dict[str, Any] | None:
    item = event.get("item")
    if isinstance(item, dict):
        return item
    if event.get("type") in {"command_execution", "file_change", "agent_message"}:
        return event
    return None


def _command_from_item(item: dict[str, Any]) -> str | None:
    if item.get("type") not in {"command_execution", "command"}:
        return None
    command = item.get("command")
    exit_code = item.get("exit_code")
    if not isinstance(command, str) or not command.strip():
        return None
    if not isinstance(exit_code, int) or isinstance(exit_code, bool):
        return None
    return command


def _read_paths(task: dict[str, Any], raw_output: str) -> set[str]:
    candidates = {
        grader._safe_relative(path)
        for path in [*task.get("fixture_files", {}), *task.get("snapshot_files", [])]
        if grader._safe_relative(path) is not None
    }
    reads: set[str] = set()
    for line in raw_output.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        item = _raw_item(event)
        if item is None:
            continue
        command = _command_from_item(item)
        if command is not None:
            reads.update(
                capture_codex._read_paths_from_command(
                    command,
                    Path("<fixture-root>"),
                    candidates,
                )
            )
    return reads


def _forbidden_paths(trace_events: list[dict[str, Any]], task: dict[str, Any]) -> list[str]:
    forbidden = {
        grader._safe_relative(path)
        for path in task.get("forbidden_reads", [])
        if grader._safe_relative(path) is not None
    }
    reads = {
        grader._safe_relative(event.get("path"))
        for event in trace_events
        if event.get("event") == "file_read"
    }
    return sorted(path for path in reads & forbidden if path is not None)


def _rebuild_trace(task: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    manifest = _load_json(run_dir / "run.json")
    trace_path = run_dir / str(manifest["trace_path"])
    raw_path = run_dir / str(manifest["raw_trace_path"])
    old_events = [
        json.loads(line)
        for line in trace_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    raw_output = raw_path.read_text(encoding="utf-8")
    old_forbidden = _forbidden_paths(old_events, task)
    reads = _read_paths(task, raw_output)
    base_events = [
        event
        for event in old_events
        if event.get("event") not in {"file_read", "file_written", "diff_snapshot"}
    ]
    written_events = [
        event for event in old_events if event.get("event") == "file_written"
    ]
    diff_events = [
        event for event in old_events if event.get("event") == "diff_snapshot"
    ]
    events = list(base_events)
    events.extend(
        {
            "sequence": 0,
            "event": "file_read",
            "path": path,
            "source": "command_inference",
            "basis": "command_text",
        }
        for path in sorted(reads)
    )
    events.extend(written_events)
    events.extend(diff_events[-1:])
    for sequence, event in enumerate(events):
        event["sequence"] = sequence
    trace_path.write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n",
        encoding="utf-8",
    )
    capture_codex._write_hashes(run_dir, manifest)
    new_forbidden = sorted(
        path
        for path in reads
        if path in {
            grader._safe_relative(item)
            for item in task.get("forbidden_reads", [])
        }
    )
    return {
        "old_forbidden_reads": old_forbidden,
        "new_forbidden_reads": new_forbidden,
        "changed": old_forbidden != new_forbidden,
    }


def _retry_missing(
    project_root: Path,
    root: Path,
    tasks_root: Path,
    manifest: dict[str, Any],
    timeout: int,
) -> list[dict[str, Any]]:
    retried: list[dict[str, Any]] = []
    for job in manifest.get("jobs", []):
        task_id = str(job["task_id"])
        run_dir = root / task_id / str(job["profile"]) / str(job["run_id"])
        if (run_dir / "run.json").is_file():
            continue
        task_path = tasks_root / f"{task_id}.json"
        try:
            created_dir, result = capture_codex.capture_run(
                project_root=project_root,
                task_path=task_path,
                benchmarks_root=root,
                profile=str(job["profile"]),
                run_id=str(job["run_id"]),
                condition=str(job["condition"]),
                model=str(manifest["model"]),
                timeout=timeout,
            )
            retried.append(
                {
                    "task_id": task_id,
                    "condition": job["condition"],
                    "run_id": job["run_id"],
                    "status": "completed",
                    "result_status": result.get("status"),
                    "run_dir": created_dir.relative_to(root).as_posix(),
                }
            )
        except Exception as error:
            retried.append(
                {
                    "task_id": task_id,
                    "condition": job["condition"],
                    "run_id": job["run_id"],
                    "status": "exception",
                    "exception_type": type(error).__name__,
                    "exception": type(error).__name__,
                }
            )
    return retried


def replay_batch(
    *,
    project_root: Path,
    root: Path,
    tasks_root: Path,
    retry_missing: bool,
    timeout: int,
) -> dict[str, Any]:
    manifest = _load_json(root / "batch-manifest.json")
    if manifest.get("model") != "gpt-5.6-luna":
        raise ValueError("replay only accepts the confirmed gpt-5.6-luna batch")
    retried = (
        _retry_missing(project_root, root, tasks_root, manifest, timeout)
        if retry_missing
        else []
    )
    replayed: list[dict[str, Any]] = []
    for trace_path in sorted(root.glob("**/run-*/trace.jsonl")):
        run_dir = trace_path.parent
        run_manifest = _load_json(run_dir / "run.json")
        task_path = tasks_root / f"{run_manifest['task_id']}.json"
        task = capture_codex._load_task(task_path)
        replay = _rebuild_trace(task, run_dir)
        result = grader.grade(task_path, run_dir)
        _write_json(run_dir / "result.json", result)
        replayed.append(
            {
                "run_dir": run_dir.relative_to(root).as_posix(),
                "task_id": run_manifest["task_id"],
                "condition": run_manifest["condition"],
                "run_id": run_manifest["run_id"],
                **replay,
                "result_status": result.get("status"),
            }
        )
    summary = aggregate.aggregate(root, tasks_root, write_results=True)
    _write_json(root / "summary.json", summary)
    public_evidence = export_public_evidence.export_manifest(
        root,
        root / "public-evidence.json",
    )
    replay_status = {
        "schema_version": 1,
        "runner_fix": "command-segment read attribution excludes PowerShell -PathType and Write-Output path labels",
        "public_verifier_fix": "absolute-path detection no longer flags relative separator text",
        "replayed_run_count": len(replayed),
        "retried_jobs": retried,
        "remaining_run_count": len(list(root.glob("**/run-*/run.json"))),
        "forbidden_read_corrections": sum(
            bool(item["changed"]) for item in replayed
        ),
        "replayed": replayed,
        "summary_status": summary.get("status"),
        "summary_run_count": len(summary.get("runs", [])),
        "public_evidence_run_count": public_evidence["run_count"],
    }
    _write_json(root / "replay-status.json", replay_status)
    batch_status_path = root / "batch-status.json"
    batch_status = _load_json(batch_status_path) if batch_status_path.is_file() else {}
    for job in batch_status.get("jobs", []):
        if isinstance(job, dict) and job.get("status") == "exception":
            job["exception"] = (
                f"{job.get('exception_type', 'Exception')}: command details omitted"
            )
    batch_status["replay"] = {
        "status": "completed",
        "summary_status": summary.get("status"),
        "summary_run_count": len(summary.get("runs", [])),
        "public_evidence_run_count": public_evidence["run_count"],
        "replayed_run_count": len(replayed),
        "retried_jobs": retried,
    }
    _write_json(batch_status_path, batch_status)
    return replay_status


def main() -> int:
    project_root = Path(__file__).parents[2].resolve()
    parser = argparse.ArgumentParser(description="Replay and regrade a naturalistic batch.")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--tasks-root", type=Path, default=Path("benchmarks/naturalistic/tasks"))
    parser.add_argument("--retry-missing", action="store_true")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    root = (args.root if args.root.is_absolute() else project_root / args.root).resolve()
    tasks_root = (
        args.tasks_root
        if args.tasks_root.is_absolute()
        else project_root / args.tasks_root
    ).resolve()
    try:
        result = replay_batch(
            project_root=project_root,
            root=root,
            tasks_root=tasks_root,
            retry_missing=args.retry_missing,
            timeout=args.timeout,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"replay failed: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "replayed_run_count": result["replayed_run_count"],
                "retried_jobs": result["retried_jobs"],
                "summary_status": result["summary_status"],
                "summary_run_count": result["summary_run_count"],
                "public_evidence_run_count": result["public_evidence_run_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
