from __future__ import annotations

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
    def test_aggregate_keeps_naturalistic_pairs_and_readiness_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_run(root, profile="codex-gpt-5.5", run_id="run-001", condition="with-r-doc")
            write_run(root, profile="baseline-no-r-doc", run_id="run-001", condition="baseline-no-r-doc")
            summary = aggregate.aggregate(root, PROJECT_ROOT / "benchmarks" / "naturalistic" / "tasks")
            self.assertEqual(summary["status"], "partial")
            self.assertEqual(summary["coverage"]["paired_run_count"], 1)
            self.assertFalse(summary["coverage"]["trend_readiness"])
            self.assertEqual(summary["coverage"]["task_ids"], ["api-response-field-rename"])
            self.assertEqual(len(summary["paired_comparisons"]), 1)
            self.assertEqual(summary["paired_comparisons"][0]["paired_run_ids"], ["run-001"])

    def test_no_runs_are_pending_without_a_fake_zero_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            summary = aggregate.aggregate(
                Path(directory),
                PROJECT_ROOT / "benchmarks" / "naturalistic" / "tasks",
            )
            self.assertEqual(summary["status"], "pending")
            self.assertEqual(summary["runs"], [])
            self.assertEqual(summary["coverage"]["paired_run_count"], 0)

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
            self.assertEqual(summary["coverage"]["paired_run_count"], 1)
            self.assertEqual(summary["paired_comparisons"][0]["conditions"]["with-r-doc"]["task_success"], 0.0)


if __name__ == "__main__":
    unittest.main()
