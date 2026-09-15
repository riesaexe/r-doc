from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))

import aggregate_benchmarks
import benchmark_audit
import evaluate_agent
from test_agent_evaluation import CASES, complete_evidence


CASES_PATH = Path(__file__).parents[1] / "evals" / "cases.json"


def write_run(root: Path, profile: str = "codex-gpt-5.6", run_id: str = "run-001") -> Path:
    run_dir = root / profile / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "trace.jsonl").write_text('{"event":"captured"}\n', encoding="utf-8")
    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "profile": profile,
                "run_id": run_id,
                "condition": "with-r-doc",
                "agent": "Codex",
                "model": "gpt-5.6",
                "skill_version": CASES["skill_version"],
                "captured_at": "2026-09-15T00:00:00Z",
                "source": "manual-real-agent-run",
                "trace_path": "trace.jsonl",
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "evidence.json").write_text(
        json.dumps(complete_evidence(), ensure_ascii=False),
        encoding="utf-8",
    )
    return run_dir


class BenchmarkToolTests(unittest.TestCase):
    def test_empty_benchmarks_are_explicitly_pending(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            summary, result_files = aggregate_benchmarks.aggregate(CASES, Path(directory))
            self.assertEqual(summary["status"], "pending")
            self.assertEqual(summary["runs"], [])
            self.assertEqual(result_files, [])

    def test_real_run_is_aggregated_into_profile_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_run(root)
            summary, result_files = aggregate_benchmarks.aggregate(CASES, root)
            self.assertEqual(summary["status"], "pass")
            self.assertEqual(len(result_files), 1)
            profile = summary["profiles"]["codex-gpt-5.6"]
            self.assertEqual(profile["run_count"], 1)
            self.assertEqual(profile["activation_accuracy"], 100.0)
            self.assertEqual(profile["audit_compliance"], 100.0)
            self.assertEqual(profile["unnecessary_reads_average"], 0.0)
            self.assertEqual(profile["task_success"], 100.0)

    def test_real_run_requires_a_captured_trace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir = write_run(root)
            (run_dir / "trace.jsonl").unlink()
            summary, _ = aggregate_benchmarks.aggregate(CASES, root)
            self.assertEqual(summary["status"], "fail")
            self.assertTrue(any("trace_path does not exist" in error for error in summary["errors"]))

    def test_small_audit_performance_fixture_is_clean(self) -> None:
        result = benchmark_audit.measure_size(3, iterations=1, warmup=0)
        self.assertEqual(result["findings"], 0)
        self.assertEqual(len(result["durations_seconds"]), 1)
        self.assertGreaterEqual(result["median_seconds"], 0)

    def test_machine_rule_identifier_drift_is_rejected(self) -> None:
        cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
        cases["machine_rules"]["safety"]["checks"] = ["renamed_secret_check"]
        path = Path("cases-with-drift.json")
        with patch.object(evaluate_agent, "load_json", return_value=cases):
            with self.assertRaises(ValueError):
                evaluate_agent.load_cases(path)

    def test_machine_check_registry_drift_is_rejected(self) -> None:
        with patch.dict(
            evaluate_agent.MACHINE_CHECK_IMPLEMENTATIONS,
            {"unbound_check": lambda values: True},
        ):
            with self.assertRaises(ValueError):
                evaluate_agent.load_cases(CASES_PATH)


if __name__ == "__main__":
    unittest.main()
