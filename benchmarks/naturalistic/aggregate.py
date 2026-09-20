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


SUMMARY_SCHEMA_VERSION = 3
METRICS = ("task_success", "outcome_compliance", "executable_outcome", "context_safety", "trace_integrity")
MEASUREMENT_GATE_CHECKS = {
    "manifest",
    "artifact_integrity",
    "artifact_paths",
    "trace_integrity",
    "prompt_contract",
    "final_response",
    "activation_evidence",
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


def _failure_analysis(records: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = {"pass": 0, "fail": 0}
    task_outcome_counts = {"pass": 0, "fail": 0}
    failure_modes = {
        "forbidden_read_only": 0,
        "forbidden_read_and_activation_unverified": 0,
        "activation_unverified_only": 0,
        "other": 0,
    }
    forbidden_read_runs = 0
    activation_unverified_runs = 0
    for record in records:
        status = str(record.get("status"))
        if status in status_counts:
            status_counts[status] += 1
        task_outcome_status = str(record.get("task_outcome_status"))
        if task_outcome_status in task_outcome_counts:
            task_outcome_counts[task_outcome_status] += 1
        has_forbidden_read = any(
            isinstance(error, str) and error.startswith("forbidden reads:")
            for error in record.get("errors", [])
        )
        has_activation_failure = not bool(record.get("activation_verified"))
        if has_forbidden_read:
            forbidden_read_runs += 1
        if has_activation_failure:
            activation_unverified_runs += 1
        if status != "fail":
            continue
        if has_forbidden_read and has_activation_failure:
            failure_modes["forbidden_read_and_activation_unverified"] += 1
        elif has_forbidden_read:
            failure_modes["forbidden_read_only"] += 1
        elif has_activation_failure:
            failure_modes["activation_unverified_only"] += 1
        else:
            failure_modes["other"] += 1
    return {
        "status_counts": status_counts,
        "task_outcome_status_counts": task_outcome_counts,
        "forbidden_read_runs": forbidden_read_runs,
        "activation_unverified_runs": activation_unverified_runs,
        "task_outcome_pass_but_overall_fail": sum(
            1
            for record in records
            if record.get("status") == "fail" and record.get("task_outcome_status") == "pass"
        ),
        "failure_modes": failure_modes,
    }


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


def aggregate(
    benchmarks_root: Path,
    tasks_root: Path,
    *,
    write_results: bool = False,
) -> dict[str, Any]:
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
            if write_results:
                (run_dir / "result.json").write_text(
                    json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
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
                "task_outcome_status": result.get("task_outcome_status", result.get("status")),
                "activation_verified": bool(result.get("activation_verified")),
                "measurement_valid": _measurement_valid(result),
                "metrics": result.get("metrics", {}),
                "result_path": run_dir.relative_to(benchmarks_root).joinpath("result.json").as_posix(),
                "errors": result.get("errors", []),
            }
        )

    valid = [record for record in records if record["measurement_valid"]]
    failure_analysis = _failure_analysis(records)
    activation_verified_runs = sum(1 for record in records if record["activation_verified"])
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
    task_pair_groups: dict[str, list[int]] = {}
    for comparison in comparisons:
        task_id = str(comparison["task_id"])
        pair_count_for_group = int(comparison["paired_run_count"])
        if pair_count_for_group:
            task_pair_groups.setdefault(task_id, []).append(pair_count_for_group)
    task_pair_counts = {
        task_id: min(pair_counts)
        for task_id, pair_counts in task_pair_groups.items()
    }
    paired_task_ids = sorted(task_pair_counts)
    tasks_with_trend_readiness = sorted(
        task_id for task_id, count in task_pair_counts.items() if count >= 3
    )
    tasks_with_statistical_readiness = sorted(
        task_id for task_id, count in task_pair_counts.items() if count >= 5
    )
    tasks_with_strong_evidence_readiness = sorted(
        task_id for task_id, count in task_pair_counts.items() if count >= 10
    )
    coverage = {
        "models": models,
        "model_count": len(models),
        "multi_model": len(models) >= 2,
        "task_ids": task_ids,
        "task_count": len(task_ids),
        "paired_task_ids": paired_task_ids,
        "paired_task_count": len(paired_task_ids),
        "task_diversity_ready": len(paired_task_ids) >= 4,
        "coverage_pair_count": pair_count,
        "activation_verified_run_count": activation_verified_runs,
        "activation_unverified_run_count": len(records) - activation_verified_runs,
        "task_pair_counts": dict(sorted(task_pair_counts.items())),
        "replicated_task_count": sum(count >= 2 for count in task_pair_counts.values()),
        "min_pairs_per_task": min(task_pair_counts.values(), default=0),
        "tasks_with_trend_readiness": tasks_with_trend_readiness,
        "tasks_with_statistical_readiness": tasks_with_statistical_readiness,
        "tasks_with_strong_evidence_readiness": tasks_with_strong_evidence_readiness,
        "sample_size_guidance": {
            "replication_min_pairs": 2,
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
        all_tasks_strong = bool(task_pair_counts) and all(
            count >= 10 for count in task_pair_counts.values()
        )
        status = "partial" if not all_tasks_strong else "pass"
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
            "outcome_compliance": "Narrow static contract assertions over the runner-generated final snapshot; runtime behavior is reported separately.",
            "executable_outcome": "Grader-owned pytest and behavior checks executed from the final snapshot.",
        },
        "activation_evidence": {
            "verified_runs": activation_verified_runs,
            "unverified_runs": len(records) - activation_verified_runs,
            "effect_comparisons_require_verified_activation": True,
            "limitation": "Codex JSONL does not expose OS-level skill loading telemetry; raw-event signals are recorded per run.",
        },
        "status": status,
        "failure_analysis": failure_analysis,
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
    parser.add_argument(
        "--write-results",
        action="store_true",
        help="rewrite each run's result.json from the current task specification",
    )
    args = parser.parse_args()
    try:
        summary = aggregate(
            args.root.resolve(),
            args.tasks_root.resolve(),
            write_results=args.write_results,
        )
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
