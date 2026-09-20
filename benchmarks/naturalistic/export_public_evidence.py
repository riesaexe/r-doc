from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import grader


PUBLIC_MANIFEST_SCHEMA_VERSION = 1
PATH_PATTERN = re.compile(r'(?i)(?:[a-z]:[\\/]|\\\\)[^"\r\n]+')


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, str):
        return PATH_PATTERN.sub("<redacted-path>", value)
    return value


def _critical_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid normalized trace at {path}:{line_number}: {error}") from error
        if not isinstance(event, dict):
            raise ValueError(f"normalized trace event is not an object: {path}:{line_number}")
        if event.get("event") in {"prompt", "command", "file_read", "file_written", "diff_snapshot"}:
            events.append(_sanitize(event))
    return events


def _exported_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _public_run(root: Path, run_dir: Path) -> dict[str, Any]:
    manifest = _load_json(run_dir / "run.json")
    result = _load_json(run_dir / "result.json")
    hashes = _load_json(run_dir / "artifact-hashes.json")
    trace = _critical_events(run_dir / str(manifest.get("trace_path", "trace.jsonl")))
    relative_dir = run_dir.relative_to(root).as_posix()
    public_result = _sanitize(
        {
            key: result.get(key)
            for key in (
                "schema_version",
                "status",
                "benchmark_kind",
                "grader_kind",
                "task_id",
                "condition",
                "agent",
                "model",
                "activation_verified",
                "metrics",
                "checks",
                "errors",
                "read_attribution",
            )
        }
    )
    public_run = _sanitize(
        {
            key: manifest.get(key)
            for key in (
                "schema_version",
                "profile",
                "run_id",
                "condition",
                "benchmark_kind",
                "prompt_contract",
                "activation_ground_truth",
                "grader_kind",
                "review_provenance",
                "skill_version",
                "activation_evidence",
                "capture_environment",
                "task_id",
                "agent",
                "model",
                "captured_at",
            )
        }
    )
    if "capture_metrics" in manifest:
        public_run["capture_metrics"] = _sanitize(manifest["capture_metrics"])
    public_run["run_dir"] = relative_dir
    public_run["source_artifact_hashes"] = _sanitize(hashes)
    public_run["critical_events"] = trace
    public_run["result"] = public_result
    public_run["exported_hashes"] = {
        "manifest": _exported_hash(public_run),
        "result": _exported_hash(public_result),
        "critical_events": _exported_hash(trace),
    }
    return public_run


def export_manifest(source_root: Path, output: Path) -> dict[str, Any]:
    source_root = source_root.resolve()
    if not source_root.is_dir():
        raise ValueError(f"naturalistic root does not exist: {source_root}")
    runs = [
        _public_run(source_root, manifest_path.parent)
        for manifest_path in sorted(source_root.glob("**/run-*/run.json"))
    ]
    summary = _sanitize(_load_json(source_root / "summary.json")) if (source_root / "summary.json").is_file() else None
    payload = {
        "schema_version": PUBLIC_MANIFEST_SCHEMA_VERSION,
        "benchmark_kind": grader.NATURALISTIC_BENCHMARK_KIND,
        "source_root": "<redacted-benchmark-root>",
        "raw_artifacts_retained_locally": True,
        "public_artifact_policy": "sanitized-manifest-critical-events-result-and-source-hashes",
        "verification": {
            "verifier": "benchmarks/naturalistic/verify_public_evidence.py",
            "scope": "public-structure-and-cross-summary",
            "source_hash_replay": "requires-source-root",
        },
        "run_count": len(runs),
        "summary": summary,
        "runs": runs,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Export sanitized naturalistic benchmark evidence.")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = export_manifest(args.root, args.output)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"export failed: {error}")
        return 1
    print(json.dumps({"output": str(args.output), "run_count": payload["run_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
