from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

from evaluate_agent import evaluate, load_cases


RUN_SCHEMA_VERSION = 1
RUN_CONDITIONS = {"with-r-doc", "baseline-no-r-doc"}
REQUIRED_MANIFEST_FIELDS = (
    "schema_version",
    "profile",
    "run_id",
    "condition",
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
    for field in ("agent", "model", "captured_at", "source"):
        if not _non_empty(manifest.get(field)):
            errors.append(f"{run_dir}: run.json {field} must be non-empty")
    if manifest.get("skill_version") != expected_skill_version:
        errors.append(f"{run_dir}: run.json skill_version must match cases")

    trace_path = manifest.get("trace_path")
    if not isinstance(trace_path, str) or not trace_path.strip():
        errors.append(f"{run_dir}: run.json trace_path must be non-empty")
    else:
        trace = (run_dir / trace_path).resolve()
        try:
            trace.relative_to(run_dir.resolve())
        except ValueError:
            errors.append(f"{run_dir}: trace_path leaves the run directory")
        else:
            if not trace.is_file():
                errors.append(f"{run_dir}: trace_path does not exist: {trace_path}")
    return errors


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
            "task_success": 0.0,
        }

    activation_passes = 0
    audit_passes = 0
    task_passes = 0
    unnecessary_reads = 0
    required_reads = {
        case["id"]: set(case.get("required_files_read", []))
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
            unnecessary_reads += len(set(reads) - required_reads.get(identifier, set()))

    return {
        "activation_accuracy": round(activation_passes / count * 100, 2),
        "audit_compliance": round(audit_passes / count * 100, 2),
        "unnecessary_reads": unnecessary_reads,
        "task_success": round(task_passes / count * 100, 2),
    }


def _profile_summary(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(str(record["profile"]), []).append(record)

    summaries: dict[str, dict[str, Any]] = {}
    for profile, items in grouped.items():
        metrics = [item["metrics"] for item in items]
        summaries[profile] = {
            "run_count": len(items),
            "activation_accuracy": round(statistics.mean(item["activation_accuracy"] for item in metrics), 2),
            "audit_compliance": round(statistics.mean(item["audit_compliance"] for item in metrics), 2),
            "unnecessary_reads_average": round(statistics.mean(item["unnecessary_reads"] for item in metrics), 2),
            "unnecessary_reads_total": sum(item["unnecessary_reads"] for item in metrics),
            "task_success": round(statistics.mean(item["task_success"] for item in metrics), 2),
        }
    return summaries


def aggregate(cases: dict[str, Any], benchmarks_root: Path) -> tuple[dict[str, Any], list[tuple[Path, dict[str, Any]]]]:
    records: list[dict[str, Any]] = []
    result_files: list[tuple[Path, dict[str, Any]]] = []
    errors: list[str] = []
    if not benchmarks_root.is_dir():
        return (
            {
                "schema_version": RUN_SCHEMA_VERSION,
                "evaluation_skill_version": cases.get("skill_version"),
                "status": "pending",
                "profiles": {},
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
            manifest_errors = _validate_manifest(
                manifest,
                run_dir,
                profile,
                run_id,
                str(cases.get("skill_version", "")),
            )
            errors.extend(manifest_errors)
            result = evaluate(cases, evidence)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"{run_dir}: {error}")
            continue

        metrics = _scenario_metrics(result, evidence, cases)
        records.append(
            {
                "profile": profile,
                "run_id": run_id,
                "condition": manifest.get("condition"),
                "agent": manifest.get("agent"),
                "model": manifest.get("model"),
                "captured_at": manifest.get("captured_at"),
                "status": result.get("status"),
                "percentage": result.get("percentage", 0.0),
                "metrics": metrics,
                "evidence_path": str(evidence_path.as_posix()),
                "trace_path": str((run_dir / str(manifest.get("trace_path", ""))).as_posix()),
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
        "schema_version": RUN_SCHEMA_VERSION,
        "evaluation_skill_version": cases.get("skill_version"),
        "status": status,
        "profiles": _profile_summary(records),
        "runs": records,
        "errors": errors,
        "notes": (
            "No real agent benchmark runs have been captured yet."
            if not records and not errors
            else (
                "Metrics are derived from real captured evidence. "
                "unnecessary_reads counts unique files read beyond each case's required files."
            )
        ),
    }
    return summary, result_files


def main() -> int:
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
