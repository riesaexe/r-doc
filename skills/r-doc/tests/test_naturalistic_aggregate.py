from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "benchmarks" / "naturalistic"))
sys.path.insert(0, str(Path(__file__).parent))

import aggregate
from test_naturalistic_grader import write_run


class NaturalisticAggregateTests(unittest.TestCase):
    def test_write_results_replays_the_current_grader_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_run(
                root,
                profile="codex-gpt-5.5",
                run_id="run-001",
                condition="with-r-doc",
            )
            result_path = root / "codex-gpt-5.5" / "run-001" / "result.json"
            result_path.write_text(json.dumps({"status": "stale"}), encoding="utf-8")
            aggregate.aggregate(
                root,
                PROJECT_ROOT / "benchmarks" / "naturalistic" / "tasks",
                write_results=True,
            )
            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertNotEqual(result["status"], "stale")
            self.assertIn("activation_verified", result)

    def test_aggregate_keeps_naturalistic_pairs_and_readiness_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_run(root, profile="codex-gpt-5.5", run_id="run-001", condition="with-r-doc")
            write_run(root, profile="baseline-no-r-doc", run_id="run-001", condition="baseline-no-r-doc")
            summary = aggregate.aggregate(root, PROJECT_ROOT / "benchmarks" / "naturalistic" / "tasks")
            self.assertEqual(summary["status"], "partial")
            self.assertEqual(summary["coverage"]["coverage_pair_count"], 1)
            self.assertFalse(summary["coverage"]["task_diversity_ready"])
            self.assertEqual(summary["coverage"]["replicated_task_count"], 0)
            self.assertEqual(summary["coverage"]["min_pairs_per_task"], 1)
            self.assertEqual(summary["coverage"]["tasks_with_trend_readiness"], [])
            self.assertEqual(summary["coverage"]["task_ids"], ["api-response-field-rename"])
            self.assertEqual(len(summary["paired_comparisons"]), 1)
            self.assertEqual(summary["paired_comparisons"][0]["paired_run_ids"], ["run-001"])
            self.assertFalse(Path(summary["runs"][0]["result_path"]).is_absolute())

    def test_no_runs_are_pending_without_a_fake_zero_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            summary = aggregate.aggregate(
                Path(directory),
                PROJECT_ROOT / "benchmarks" / "naturalistic" / "tasks",
            )
            self.assertEqual(summary["status"], "pending")
            self.assertEqual(summary["runs"], [])
            self.assertEqual(summary["coverage"]["coverage_pair_count"], 0)
            self.assertEqual(summary["coverage"]["min_pairs_per_task"], 0)

    def test_structurally_valid_failed_outcomes_still_count_as_measurements(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_run(
                root,
                profile="codex-gpt-5.5",
                run_id="run-001",
                condition="with-r-doc",
                forbidden_read=True,
            )
            write_run(
                root,
                profile="baseline-no-r-doc",
                run_id="run-001",
                condition="baseline-no-r-doc",
                forbidden_read=True,
            )
            summary = aggregate.aggregate(root, PROJECT_ROOT / "benchmarks" / "naturalistic" / "tasks")
            self.assertEqual(summary["status"], "partial")
            self.assertEqual(summary["coverage"]["coverage_pair_count"], 1)
            self.assertEqual(summary["paired_comparisons"][0]["conditions"]["with-r-doc"]["task_success"], 0.0)
            self.assertEqual(summary["failure_analysis"]["forbidden_read_runs"], 2)
            self.assertEqual(summary["failure_analysis"]["failure_modes"]["forbidden_read_only"], 2)

    def test_top_level_readiness_requires_repeated_pairs_for_the_same_task(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for run_id in ("run-001", "run-002", "run-003"):
                write_run(root, profile="codex-gpt-5.5", run_id=run_id, condition="with-r-doc")
                write_run(root, profile="baseline-no-r-doc", run_id=run_id, condition="baseline-no-r-doc")
            summary = aggregate.aggregate(root, PROJECT_ROOT / "benchmarks" / "naturalistic" / "tasks")
            coverage = summary["coverage"]
            self.assertEqual(coverage["coverage_pair_count"], 3)
            self.assertEqual(coverage["replicated_task_count"], 1)
            self.assertEqual(coverage["min_pairs_per_task"], 3)
            self.assertEqual(coverage["tasks_with_trend_readiness"], ["api-response-field-rename"])
            self.assertNotIn("trend_readiness", coverage)

    def test_second_model_does_not_count_as_same_model_replication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for model in ("gpt-5.5", "gpt-5.6"):
                write_run(
                    root,
                    profile=f"codex-{model}",
                    run_id="run-001",
                    condition="with-r-doc",
                    model=model,
                )
                write_run(
                    root,
                    profile=f"baseline-{model}",
                    run_id="run-001",
                    condition="baseline-no-r-doc",
                    model=model,
                )
            summary = aggregate.aggregate(root, PROJECT_ROOT / "benchmarks" / "naturalistic" / "tasks")
            coverage = summary["coverage"]
            self.assertEqual(coverage["coverage_pair_count"], 2)
            self.assertEqual(coverage["task_pair_counts"], {"api-response-field-rename": 1})
            self.assertEqual(coverage["replicated_task_count"], 0)
            self.assertEqual(coverage["min_pairs_per_task"], 1)
            self.assertFalse(coverage["tasks_with_trend_readiness"])


if __name__ == "__main__":
    unittest.main()
