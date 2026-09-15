from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

import grader


SUMMARY_SCHEMA_VERSION = 2
METRICS = ("task_success", "outcome_compliance", "executable_outcome", "context_safety", "trace_integrity")
MEASUREMENT_GATE_CHECKS = {
    "manifest",
    "artifact_integrity",
    "artifact_paths",
    "trace_integrity",
    "prompt_contract",
    "final_response",
}
T_CRITICAL_95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "mean": None,
            "median": None,
            "stdev": None,
            "ci95_low": None,
            "ci95_high": None,
            "ci95_method": "unavailable-without-pairs",
        }
    mean = statistics.mean(values)
    stdev = statistics.stdev(values) if len(values) > 1 else 0.0
    if len(values) > 1:
        critical = T_CRITICAL_95.get(len(values) - 1, 1.96)
        half_width = critical * stdev / math.sqrt(len(values))
        ci95_low: float | None = round(mean - half_width, 2)
        ci95_high: float | None = round(mean + half_width, 2)
        method = "student-t-95"
    else:
        ci95_low = None
        ci95_high = None
        method = "unavailable-below-two-pairs"
    return {
        "mean": round(mean, 2),
        "median": round(statistics.median(values), 2),
        "stdev": round(stdev, 2),
        "ci95_low": ci95_low,
        "ci95_high": ci95_high,
        "ci95_method": method,
    }


def _metric_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {"run_count": len(records)}
    for metric in METRICS:
        summary[metric] = round(
            statistics.mean(float(record["metrics"].get(metric, 0.0)) for record in records),
            2,
        ) if records else None
    return summary


def _measurement_valid(result: dict[str, Any]) -> bool:
    checks = {
        check.get("id"): check.get("status")
        for check in result.get("checks", [])
        if isinstance(check, dict)
    }
    return all(checks.get(check_id) == "pass" for check_id in MEASUREMENT_GATE_CHECKS)


def _find_tasks(tasks_root: Path) -> dict[str, Path]:
    tasks: dict[str, Path] = {}
    for path in sorted(tasks_root.glob("*.json")):
        task = _load_json(path)
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            continue
        if task_id in tasks:
            raise ValueError(f"duplicate naturalistic task_id: {task_id}")
        tasks[task_id] = path
    return tasks


def _pair_comparisons(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    valid = [record for record in records if record["measurement_valid"]]
    grouped: dict[tuple[str, str, str], dict[str, dict[str, list[dict[str, Any]]]]] = {}
    for record in valid:
        key = (str(record["agent"]), str(record["model"]), str(record["task_id"]))
        grouped.setdefault(key, {}).setdefault(str(record["condition"]), {}).setdefault(
            str(record["run_id"]), []
        ).append(record)

    comparisons: list[dict[str, Any]] = []
    for (agent, model, task_id), by_condition in sorted(grouped.items()):
        with_runs = by_condition.get("with-r-doc", {})
        baseline_runs = by_condition.get("baseline-no-r-doc", {})
        paired_ids = sorted(
            run_id
            for run_id in set(with_runs) & set(baseline_runs)
            if len(with_runs[run_id]) == 1 and len(baseline_runs[run_id]) == 1
        )
        delta_values = {metric: [] for metric in METRICS}
        per_run: list[dict[str, Any]] = []
        for run_id in paired_ids:
            with_record = with_runs[run_id][0]
            baseline_record = baseline_runs[run_id][0]
            delta = {
                metric: round(
                    float(with_record["metrics"].get(metric, 0.0))
                    - float(baseline_record["metrics"].get(metric, 0.0)),
                    2,
                )
                for metric in METRICS
            }
            for metric, value in delta.items():
                delta_values[metric].append(value)
            per_run.append({"run_id": run_id, "delta": delta})
        comparisons.append(
            {
                "agent": agent,
                "model": model,
                "task_id": task_id,
                "paired_run_count": len(paired_ids),
                "paired_run_ids": paired_ids,
                "unpaired_run_counts": {
                    "with-r-doc": len(with_runs) - len(paired_ids),
                    "baseline-no-r-doc": len(baseline_runs) - len(paired_ids),
                },
                "trend_readiness": len(paired_ids) >= 3,
                "statistical_readiness": len(paired_ids) >= 5,
                "strong_evidence_readiness": len(paired_ids) >= 10,
                "conditions": {
                    "with-r-doc": _metric_summary([with_runs[item][0] for item in paired_ids]),
                    "baseline-no-r-doc": _metric_summary([baseline_runs[item][0] for item in paired_ids]),
                },
                "delta": {
                    metric: round(statistics.mean(values), 2) if values else None
                    for metric, values in delta_values.items()
                },
                "delta_statistics": {
                    metric: _stats(values) for metric, values in delta_values.items() if values
                },
                "per_run_deltas": per_run,
            }
        )
    return comparisons


def aggregate(benchmarks_root: Path, tasks_root: Path) -> dict[str, Any]:
    tasks = _find_tasks(tasks_root)
    errors: list[str] = []
    records: list[dict[str, Any]] = []
    if benchmarks_root.is_dir():
        run_paths = sorted(benchmarks_root.glob("**/run-*/run.json"))
    else:
        run_paths = []
    for manifest_path in run_paths:
        run_dir = manifest_path.parent
        try:
            manifest = _load_json(manifest_path)
            task_id = manifest.get("task_id")
            task_path = tasks.get(task_id)
            if task_path is None:
                raise ValueError(f"unknown naturalistic task_id: {task_id}")
            result = grader.grade(task_path, run_dir)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"{run_dir}: {error}")
            continue
        records.append(
            {
                "profile": manifest.get("profile", run_dir.parent.name),
                "run_id": manifest.get("run_id", run_dir.name),
                "condition": manifest.get("condition"),
                "task_id": manifest.get("task_id"),
                "agent": manifest.get("agent"),
                "model": manifest.get("model"),
                "status": result.get("status"),
                "measurement_valid": _measurement_valid(result),
                "metrics": result.get("metrics", {}),
                "result_path": run_dir.joinpath("result.json").as_posix(),
                "errors": result.get("errors", []),
            }
        )

    valid = [record for record in records if record["measurement_valid"]]
    profiles: dict[str, dict[str, Any]] = {}
    by_profile: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for record in valid:
        by_profile.setdefault(record["profile"], {}).setdefault(record["condition"], []).append(record)
    for profile, by_condition in sorted(by_profile.items()):
        profiles[profile] = {
            "run_count": sum(len(items) for items in by_condition.values()),
            "conditions": {
                condition: _metric_summary(items)
                for condition, items in sorted(by_condition.items())
            },
        }

    comparisons = _pair_comparisons(records)
    pair_count = sum(item["paired_run_count"] for item in comparisons)
    models = sorted({str(record["model"]) for record in valid})
    task_ids = sorted({str(record["task_id"]) for record in valid})
    coverage = {
        "models": models,
        "model_count": len(models),
        "multi_model": len(models) >= 2,
        "task_ids": task_ids,
        "task_count": len(task_ids),
        "task_diversity": len(task_ids) >= 4,
        "paired_run_count": pair_count,
        "trend_readiness": pair_count >= 3,
        "statistical_readiness": pair_count >= 5,
        "strong_evidence_readiness": pair_count >= 10,
        "sample_size_guidance": {
            "trend_min_pairs": 3,
            "statistical_min_pairs": 5,
            "strong_evidence_min_pairs": 10,
            "multi_model_min_models": 2,
            "task_diversity_min_tasks": 4,
        },
    }
    if not records:
        status = "pending" if not errors else "fail"
    elif errors or any(not record["measurement_valid"] for record in records):
        status = "fail"
    else:
        status = "partial" if not coverage["strong_evidence_readiness"] else "pass"
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "benchmark_kind": grader.NATURALISTIC_BENCHMARK_KIND,
        "benchmark_name": "Naturalistic Effectiveness Benchmark",
        "prompt_contract": grader.NATURALISTIC_PROMPT_CONTRACT,
        "activation_ground_truth": grader.NATURALISTIC_ACTIVATION_GROUND_TRUTH,
        "grader_kind": grader.NATURALISTIC_GRADER_KIND,
        "review_provenance": grader.NATURALISTIC_REVIEW_PROVENANCE,
        "metric_semantics": {
            "task_success": "Independent runner snapshot, executable outcome checks, and trace safety; not agent self-report.",
            "outcome_compliance": "Static assertions over the runner-generated final snapshot.",
            "executable_outcome": "Grader-owned pytest and behavior checks executed from the final snapshot.",
        },
        "status": status,
        "coverage": coverage,
        "profiles": profiles,
        "paired_comparisons": comparisons,
        "runs": records,
        "errors": errors,
        "notes": (
            "No real naturalistic runs have been captured yet."
            if not records
            else "Naturalistic records are regenerated by the independent grader; structurally valid failed outcomes remain visible and are included as measured zero-success outcomes."
        ),
    }


def main() -> int:
    project_root = Path(__file__).parents[2].resolve()
    parser = argparse.ArgumentParser(description="Aggregate independently graded naturalistic Codex runs.")
    parser.add_argument("--root", type=Path, default=project_root / "benchmarks" / "naturalistic-runs")
    parser.add_argument("--tasks-root", type=Path, default=project_root / "benchmarks" / "naturalistic" / "tasks")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        summary = aggregate(args.root.resolve(), args.tasks_root.resolve())
        output = args.output.resolve() if args.output else args.root.resolve() / "summary.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR {error}", file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] in {"partial", "pass", "pending"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
