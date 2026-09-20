from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

import aggregate
import capture_codex
import export_public_evidence


DEFAULT_TASK_IDS = (
    "api-response-field-rename",
    "cli-option-rename",
    "event-payload-rename-v2",
    "sql-column-rename",
    "architecture-decision-sync-v1",
    "cross-module-contract-migration-v1",
    "release-doc-drift-v1",
)
CONDITIONS = ("with-r-doc", "baseline-no-r-doc")
RUNNER_PREFLIGHT_VERSION = "skill-discovery-safe-read-preflight-v2-command-glob"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _resolve(project_root: Path, value: Path) -> Path:
    return (value if value.is_absolute() else project_root / value).resolve()


def _relative_or_label(path: Path, project_root: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return "<outside-project-root>"


def _sanitize_error(error: BaseException, project_root: Path, batch_root: Path) -> str:
    text = str(error).splitlines()[0] if str(error).splitlines() else type(error).__name__
    for path, label in (
        (str(project_root), "<project-root>"),
        (str(batch_root), "<batch-root>"),
    ):
        text = text.replace(path, label).replace(path.replace("\\", "/"), label)
    text = re.sub(r"(?i)(?:[a-z]:[\\/]+|/c/)[^'\", ]+", "<redacted-path>", text)
    return text[:500]


def _build_jobs(
    task_ids: tuple[str, ...],
    run_ids: tuple[str, ...],
    profile_suffix: str,
) -> list[dict[str, str]]:
    jobs: list[dict[str, str]] = []
    for task_id in task_ids:
        for condition in CONDITIONS:
            profile = f"{condition}-gpt-5.6-luna-{profile_suffix}"
            for run_id in run_ids:
                jobs.append(
                    {
                        "task_id": task_id,
                        "condition": condition,
                        "profile": profile,
                        "run_id": run_id,
                    }
                )
    return jobs


def _run_job(
    job: dict[str, str],
    *,
    project_root: Path,
    tasks_root: Path,
    batch_root: Path,
    timeout: int,
) -> dict[str, Any]:
    task_path = tasks_root / f"{job['task_id']}.json"
    try:
        run_dir, result = capture_codex.capture_run(
            project_root=project_root,
            task_path=task_path,
            benchmarks_root=batch_root,
            profile=job["profile"],
            run_id=job["run_id"],
            condition=job["condition"],
            model="gpt-5.6-luna",
            timeout=timeout,
        )
        return {
            **job,
            "status": "completed",
            "result_status": result.get("status"),
            "run_dir": run_dir.relative_to(batch_root).as_posix(),
        }
    except Exception as error:
        return {
            **job,
            "status": "exception",
            "result_status": None,
            "exception_type": type(error).__name__,
            "exception": _sanitize_error(error, project_root, batch_root),
        }


def _status_payload(
    *,
    status: str,
    manifest: dict[str, Any],
    started_at: str,
    jobs: list[dict[str, Any]],
    elapsed_seconds: float,
    summary_status: str | None = None,
) -> dict[str, Any]:
    result_status_counts: dict[str, int] = {}
    exceptions = 0
    for job in jobs:
        if job.get("status") == "exception":
            exceptions += 1
        result_status = job.get("result_status")
        if isinstance(result_status, str):
            result_status_counts[result_status] = result_status_counts.get(result_status, 0) + 1
    payload: dict[str, Any] = {
        "schema_version": 1,
        "status": status,
        "batch_kind": manifest["batch_kind"],
        "model": manifest["model"],
        "skill_version": manifest["skill_version"],
        "runner_preflight": manifest["runner_preflight"],
        "expected_run_count": manifest["expected_run_count"],
        "completed_jobs": len(jobs),
        "exception_count": exceptions,
        "result_status_counts": dict(sorted(result_status_counts.items())),
        "started_at": started_at,
        "duration_seconds": round(elapsed_seconds, 3),
        "summary_status": summary_status,
        "jobs": sorted(
            jobs,
            key=lambda item: (
                item["task_id"],
                item["condition"],
                item["run_id"],
            ),
        ),
    }
    return payload


def run_batch(
    *,
    project_root: Path,
    batch_root: Path,
    tasks_root: Path,
    task_ids: tuple[str, ...],
    run_count: int,
    max_workers: int,
    timeout: int,
    profile_suffix: str,
) -> dict[str, Any]:
    if batch_root.exists() and any(batch_root.iterdir()):
        raise ValueError(f"batch root must be new or empty: {batch_root}")
    if not tasks_root.is_dir():
        raise ValueError(f"tasks root does not exist: {tasks_root}")
    if run_count <= 0 or max_workers <= 0 or timeout <= 0:
        raise ValueError("run-count, max-workers, and timeout must be positive")

    task_paths: dict[str, Path] = {}
    for task_id in task_ids:
        task_path = tasks_root / f"{task_id}.json"
        if not task_path.is_file():
            raise ValueError(f"task file does not exist: {task_path}")
        task = capture_codex._load_task(task_path)
        if task.get("task_id") != task_id:
            raise ValueError(f"task_id does not match filename: {task_path}")
        task_paths[task_id] = task_path

    version = (project_root / "VERSION").read_text(encoding="utf-8-sig").strip()
    run_ids = tuple(f"run-{index:03d}" for index in range(1, run_count + 1))
    jobs = _build_jobs(task_ids, run_ids, profile_suffix)
    batch_root.mkdir(parents=True, exist_ok=True)
    started_at = _now()
    manifest = {
        "schema_version": 1,
        "batch_kind": "naturalistic-effectiveness-full",
        "scope": "paired naturalistic effectiveness with existing rename tasks and complex governance tasks",
        "skill_version": version,
        "model": "gpt-5.6-luna",
        "runner": "benchmarks/naturalistic/capture_codex.py",
        "runner_preflight": RUNNER_PREFLIGHT_VERSION,
        "root": _relative_or_label(batch_root, project_root),
        "tasks_root": _relative_or_label(tasks_root, project_root),
        "task_ids": list(task_ids),
        "run_ids": list(run_ids),
        "conditions": list(CONDITIONS),
        "expected_run_count": len(jobs),
        "max_workers": max_workers,
        "timeout_seconds": timeout,
        "started_at": started_at,
        "user_confirmation": "confirmed-in-conversation",
        "shared_safe_read_preflight": True,
        "jobs": [
            {
                **job,
                "task_path": _relative_or_label(
                    tasks_root / f"{job['task_id']}.json",
                    project_root,
                ),
            }
            for job in jobs
        ],
    }
    _write_json(batch_root / "batch-manifest.json", manifest)
    _write_json(
        batch_root / "batch-status.json",
        _status_payload(
            status="running",
            manifest=manifest,
            started_at=started_at,
            jobs=[],
            elapsed_seconds=0.0,
        ),
    )

    completed_jobs: list[dict[str, Any]] = []
    start_clock = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _run_job,
                job,
                project_root=project_root,
                tasks_root=tasks_root,
                batch_root=batch_root,
                timeout=timeout,
            ): job
            for job in jobs
        }
        for index, future in enumerate(as_completed(futures), start=1):
            outcome = future.result()
            completed_jobs.append(outcome)
            _write_json(
                batch_root / "batch-status.json",
                _status_payload(
                    status="running",
                    manifest=manifest,
                    started_at=started_at,
                    jobs=completed_jobs,
                    elapsed_seconds=time.perf_counter() - start_clock,
                ),
            )
            result_status = outcome.get("result_status") or outcome.get("status")
            print(
                f"[{index}/{len(jobs)}] {outcome['task_id']} "
                f"{outcome['condition']} {outcome['run_id']} {result_status}",
                flush=True,
            )

    summary = aggregate.aggregate(batch_root, tasks_root, write_results=True)
    _write_json(batch_root / "summary.json", summary)
    public_evidence = export_public_evidence.export_manifest(
        batch_root,
        batch_root / "public-evidence.json",
    )
    final_status = _status_payload(
        status="completed",
        manifest=manifest,
        started_at=started_at,
        jobs=completed_jobs,
        elapsed_seconds=time.perf_counter() - start_clock,
        summary_status=str(summary.get("status")),
    )
    final_status["summary_run_count"] = len(summary.get("runs", []))
    final_status["public_evidence_run_count"] = public_evidence["run_count"]
    _write_json(batch_root / "batch-status.json", final_status)
    return {
        "manifest": manifest,
        "status": final_status,
        "summary": summary,
        "public_evidence_run_count": public_evidence["run_count"],
    }


def main() -> int:
    project_root = Path(__file__).parents[2].resolve()
    parser = argparse.ArgumentParser(description="Run a paired naturalistic Codex benchmark batch.")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--tasks-root", type=Path, default=Path("benchmarks/naturalistic/tasks"))
    parser.add_argument("--model", required=True)
    parser.add_argument("--task-id", action="append")
    parser.add_argument("--run-count", type=int, default=10)
    parser.add_argument("--max-workers", type=int, default=6)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--profile-suffix", default="v0.4.0-full-v1-complex")
    args = parser.parse_args()
    if args.model != "gpt-5.6-luna":
        parser.error("this confirmed batch requires --model gpt-5.6-luna")
    task_ids = tuple(args.task_id) if args.task_id else DEFAULT_TASK_IDS
    try:
        result = run_batch(
            project_root=project_root,
            batch_root=_resolve(project_root, args.root),
            tasks_root=_resolve(project_root, args.tasks_root),
            task_ids=task_ids,
            run_count=args.run_count,
            max_workers=args.max_workers,
            timeout=args.timeout,
            profile_suffix=args.profile_suffix,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"batch failed before completion: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": result["status"]["status"],
                "summary_status": result["summary"]["status"],
                "completed_jobs": result["status"]["completed_jobs"],
                "expected_run_count": result["status"]["expected_run_count"],
                "public_evidence_run_count": result["public_evidence_run_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
