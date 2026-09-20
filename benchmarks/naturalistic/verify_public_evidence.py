from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

import grader


PUBLIC_MANIFEST_SCHEMA_VERSION = 1
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ABSOLUTE_PATH = re.compile(
    r"""(?i)(?:^|[\s"'=(])(?:[a-z]:[\\/]|/{1,2}(?:users|home|private|tmp|var|opt|mnt|workspace|root)[\\/]|\\(?:users|home|private|tmp|var|opt|mnt|workspace|root)[\\/])"""
)
PRIVATE_MATERIAL = re.compile(
    r"(?i)-----begin\s+(?:rsa\s+|ec\s+|openssh\s+)?private\s+key-----|\bakia[0-9a-z]{16}\b"
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _safe_relative(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.replace("\\\\", "/")
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


def _walk_public_values(value: Any, location: str, errors: list[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _walk_public_values(item, f"{location}.{key}", errors)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _walk_public_values(item, f"{location}[{index}]", errors)
        return
    if not isinstance(value, str):
        return
    if ABSOLUTE_PATH.search(value):
        errors.append(f"absolute path is exposed at {location}")
    if PRIVATE_MATERIAL.search(value):
        errors.append(f"private material is exposed at {location}")


def _validate_hash_manifest(value: Any, location: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{location} must be an object")
        return
    if value.get("schema_version") != grader.HASH_SCHEMA_VERSION:
        errors.append(f"{location}.schema_version must be {grader.HASH_SCHEMA_VERSION}")
    if value.get("algorithm") != "sha256":
        errors.append(f"{location}.algorithm must be sha256")
    if value.get("canonicalization") != grader.HASH_CANONICALIZATION:
        errors.append(f"{location}.canonicalization must be {grader.HASH_CANONICALIZATION}")
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        errors.append(f"{location}.artifacts must be a non-empty object")
        return
    for raw_path, metadata in artifacts.items():
        safe_path = _safe_relative(raw_path)
        if safe_path is None:
            errors.append(f"{location}.artifacts has an unsafe path: {raw_path!r}")
        if not isinstance(metadata, dict) or not HEX64.fullmatch(str(metadata.get("sha256", ""))):
            errors.append(f"{location}.artifacts[{raw_path!r}].sha256 is not a 64-digit hex digest")
        elif metadata.get("canonicalization") != grader.HASH_CANONICALIZATION:
            errors.append(f"{location}.artifacts[{raw_path!r}] has the wrong canonicalization")


def _validate_events(events: Any, location: str, errors: list[str]) -> None:
    if not isinstance(events, list):
        errors.append(f"{location} must be a list")
        return
    previous = -1
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            errors.append(f"{location}[{index}] must be an object")
            continue
        sequence = event.get("sequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence <= previous:
            errors.append(f"{location}[{index}].sequence must be strictly increasing")
        else:
            previous = sequence
    if events and isinstance(events[0], dict) and events[0].get("sequence") != 0:
        errors.append(f"{location} must start at sequence 0")


def _run_identity(run: dict[str, Any]) -> tuple[Any, ...]:
    return (run.get("task_id"), run.get("condition"), run.get("model"), run.get("run_id"))


def _validate_run(run: Any, index: int, errors: list[str]) -> None:
    location = f"runs[{index}]"
    if not isinstance(run, dict):
        errors.append(f"{location} must be an object")
        return
    for field in ("run_id", "task_id", "model", "condition", "run_dir", "result"):
        if field not in run:
            errors.append(f"{location} is missing {field}")
    if run.get("condition") not in {"with-r-doc", "baseline-no-r-doc"}:
        errors.append(f"{location}.condition is invalid")
    if _safe_relative(run.get("run_dir")) is None:
        errors.append(f"{location}.run_dir must be a safe relative path")
    if not isinstance(run.get("result"), dict):
        errors.append(f"{location}.result must be an object")
    _validate_hash_manifest(run.get("source_artifact_hashes"), f"{location}.source_artifact_hashes", errors)
    _validate_events(run.get("critical_events"), f"{location}.critical_events", errors)
    exported_hashes = run.get("exported_hashes")
    if not isinstance(exported_hashes, dict):
        errors.append(f"{location}.exported_hashes must be an object")
    else:
        for field in ("manifest", "result", "critical_events"):
            if not HEX64.fullmatch(str(exported_hashes.get(field, ""))):
                errors.append(f"{location}.exported_hashes.{field} is not a 64-digit hex digest")
        manifest_view = dict(run)
        manifest_view.pop("exported_hashes", None)
        if exported_hashes.get("manifest") != _canonical_hash(manifest_view):
            errors.append(f"{location}.exported_hashes.manifest does not match the public run")
        if exported_hashes.get("result") == _canonical_hash(run.get("result")):
            pass
        else:
            errors.append(f"{location}.exported_hashes.result does not match result")
        if exported_hashes.get("critical_events") != _canonical_hash(run.get("critical_events")):
            errors.append(f"{location}.exported_hashes.critical_events does not match critical_events")


def _validate_summary(summary_path: Path, public_runs: list[dict[str, Any]], errors: list[str]) -> None:
    try:
        summary = _load_json(summary_path)
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"cannot read summary {summary_path}: {error}")
        return
    if not isinstance(summary, dict):
        errors.append("summary root must be an object")
        return
    summary_runs = summary.get("runs")
    if not isinstance(summary_runs, list):
        errors.append("summary.runs must be a list")
        return
    public_ids = {_run_identity(run) for run in public_runs}
    summary_ids = {_run_identity(run) for run in summary_runs if isinstance(run, dict)}
    if public_ids != summary_ids:
        errors.append("summary identities do not exactly match public evidence identities")
    if len(summary_runs) != len(public_runs):
        errors.append("summary run count does not match public evidence")


def _verify_source_root(source_root: Path, public_runs: list[dict[str, Any]], errors: list[str]) -> None:
    if not source_root.is_dir():
        errors.append(f"source root does not exist: {source_root}")
        return
    for index, public_run in enumerate(public_runs):
        relative = _safe_relative(public_run.get("run_dir"))
        if relative is None:
            continue
        run_dir = source_root / relative
        hash_path = run_dir / "artifact-hashes.json"
        try:
            source_hashes = _load_json(hash_path)
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"runs[{index}] source hash manifest unavailable: {error}")
            continue
        if source_hashes != public_run.get("source_artifact_hashes"):
            errors.append(f"runs[{index}] source hash manifest differs from public evidence")
            continue
        artifacts = source_hashes.get("artifacts", {})
        for raw_path, metadata in artifacts.items():
            artifact = run_dir / raw_path
            if not artifact.is_file():
                errors.append(f"runs[{index}] source artifact is missing: {relative}/{raw_path}")
                continue
            actual = grader._sha256_lf(artifact)
            if actual != metadata.get("sha256"):
                errors.append(f"runs[{index}] source artifact hash mismatch: {relative}/{raw_path}")


def verify_public_evidence(
    public_evidence_path: Path,
    *,
    summary_path: Path | None = None,
    source_root: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        payload = _load_json(public_evidence_path)
    except (OSError, json.JSONDecodeError) as error:
        return {"status": "fail", "errors": [f"cannot read public evidence: {error}"]}
    if not isinstance(payload, dict):
        return {"status": "fail", "errors": ["public evidence root must be an object"]}
    if payload.get("schema_version") != PUBLIC_MANIFEST_SCHEMA_VERSION:
        errors.append(f"schema_version must be {PUBLIC_MANIFEST_SCHEMA_VERSION}")
    runs = payload.get("runs")
    if not isinstance(runs, list):
        errors.append("runs must be a list")
        runs = []
    if payload.get("run_count") != len(runs):
        errors.append("run_count does not match runs length")
    seen: set[tuple[Any, ...]] = set()
    for index, run in enumerate(runs):
        _validate_run(run, index, errors)
        if isinstance(run, dict):
            identity = _run_identity(run)
            if identity in seen:
                errors.append(f"duplicate run identity: {identity!r}")
            seen.add(identity)
    _walk_public_values(payload, "public_evidence", errors)
    public_runs = [run for run in runs if isinstance(run, dict)]
    if summary_path is not None:
        _validate_summary(summary_path, public_runs, errors)
    if source_root is not None:
        _verify_source_root(source_root, public_runs, errors)
    report = {
        "status": "pass" if not errors else "fail",
        "verification_scope": "public-structure-and-cross-summary" if summary_path else "public-structure",
        "public_evidence": str(public_evidence_path),
        "run_count": len(runs),
        "source_artifacts": "verified" if source_root is not None and not errors else "unavailable" if source_root is None else "failed",
        "errors": errors,
    }
    if source_root is None:
        report["limitations"] = ["source artifact bytes were not supplied; only public structure and hashes were checked"]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify sanitized naturalistic benchmark evidence.")
    parser.add_argument("--public-evidence", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--source-root", type=Path)
    args = parser.parse_args()
    report = verify_public_evidence(
        args.public_evidence,
        summary_path=args.summary,
        source_root=args.source_root,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
