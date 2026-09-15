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


def trace_for_evidence(manifest: dict[str, object], evidence: dict[str, object]) -> str:
    events: list[dict[str, object]] = [
        {
            "schema_version": 1,
            "sequence": 0,
            "event": "trace_start",
            "run_id": manifest["run_id"],
            "profile": manifest["profile"],
            "condition": manifest["condition"],
            "agent": manifest["agent"],
            "model": manifest["model"],
            "skill_version": manifest["skill_version"],
        }
    ]
    sequence = 1
    scenarios = evidence["scenarios"]
    assert isinstance(scenarios, list)
    for scenario in scenarios:
        assert isinstance(scenario, dict)
        identifier = scenario["id"]
        events.append({"schema_version": 1, "sequence": sequence, "event": "scenario_start", "scenario_id": identifier})
        sequence += 1
        for path in scenario["paths_checked"]:
            events.append(
                {"schema_version": 1, "sequence": sequence, "event": "path_checked", "scenario_id": identifier, "path": path}
            )
            sequence += 1
        for path in scenario["files_read"]:
            events.append(
                {"schema_version": 1, "sequence": sequence, "event": "file_read", "scenario_id": identifier, "path": path}
            )
            sequence += 1
        for command in scenario["commands"]:
            assert isinstance(command, dict)
            event: dict[str, object] = {
                "schema_version": 1,
                "sequence": sequence,
                "event": "command",
                "scenario_id": identifier,
                "exit_code": command["exit_code"],
            }
            for key in ("name", "command"):
                if key in command:
                    event[key] = command[key]
            events.append(event)
            sequence += 1
        for path in scenario["files_written"]:
            events.append(
                {"schema_version": 1, "sequence": sequence, "event": "file_written", "scenario_id": identifier, "path": path}
            )
            sequence += 1
        events.append({"schema_version": 1, "sequence": sequence, "event": "scenario_end", "scenario_id": identifier})
        sequence += 1
    events.append({"schema_version": 1, "sequence": sequence, "event": "trace_end"})
    return "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n"


def write_run(
    root: Path,
    profile: str = "codex-gpt-5.6",
    run_id: str = "run-001",
    condition: str = "with-r-doc",
    evidence: dict[str, object] | None = None,
) -> Path:
    run_dir = root / profile / run_id
    run_dir.mkdir(parents=True)
    if evidence is None:
        evidence = complete_evidence()
    manifest = {
        "schema_version": 1,
        "profile": profile,
        "run_id": run_id,
        "condition": condition,
        "agent": "Codex",
        "model": "gpt-5.6",
        "skill_version": CASES["skill_version"],
        "captured_at": "2026-09-15T00:00:00Z",
        "source": "manual-real-agent-run",
        "trace_path": "trace.jsonl",
    }
    (run_dir / "run.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    (run_dir / "evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False),
        encoding="utf-8",
    )
    (run_dir / "trace.jsonl").write_text(trace_for_evidence(manifest, evidence), encoding="utf-8")
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

    def test_trace_must_be_structured_and_match_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir = write_run(root)
            lines = (run_dir / "trace.jsonl").read_text(encoding="utf-8").splitlines()
            first_file_read = next(index for index, line in enumerate(lines) if '"event": "file_read"' in line)
            event = json.loads(lines[first_file_read])
            event["path"] = "docs/not-in-evidence.md"
            lines[first_file_read] = json.dumps(event)
            (run_dir / "trace.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
            summary, _ = aggregate_benchmarks.aggregate(CASES, root)
            self.assertEqual(summary["status"], "fail")
            self.assertTrue(any("trace/evidence mismatch" in error for error in summary["errors"]))

    def test_placeholder_trace_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir = write_run(root)
            (run_dir / "trace.jsonl").write_text('{"event":"captured"}\n', encoding="utf-8")
            summary, _ = aggregate_benchmarks.aggregate(CASES, root)
            self.assertEqual(summary["status"], "fail")
            self.assertTrue(any("unsupported event type" in error for error in summary["errors"]))
            self.assertEqual(summary["profiles"], {})
            self.assertEqual(summary["paired_comparisons"], [])

    def test_malformed_trace_json_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir = write_run(root)
            (run_dir / "trace.jsonl").write_text("not-json\n", encoding="utf-8")
            summary, _ = aggregate_benchmarks.aggregate(CASES, root)
            self.assertEqual(summary["status"], "fail")
            self.assertTrue(any("trace line 1 is not valid JSON" in error for error in summary["errors"]))

    def test_profile_summary_keeps_conditions_separate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_run(root, profile="codex-gpt-5.6", run_id="run-001", condition="with-r-doc")
            write_run(root, profile="codex-gpt-5.6", run_id="run-002", condition="baseline-no-r-doc")
            summary, _ = aggregate_benchmarks.aggregate(CASES, root)
            profile = summary["profiles"]["codex-gpt-5.6"]
            self.assertEqual(profile["conditions"]["with-r-doc"]["run_count"], 1)
            self.assertEqual(profile["conditions"]["baseline-no-r-doc"]["run_count"], 1)
            self.assertNotIn("task_success", profile)

    def test_paired_summary_matches_agent_model_and_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with_evidence = complete_evidence()
            baseline_evidence = complete_evidence()
            with_scenarios = with_evidence["scenarios"]
            assert isinstance(with_scenarios, list)
            with_interface = next(item for item in with_scenarios if item["id"] == "trace-public-interface-change")
            assert isinstance(with_interface, dict)
            with_interface["files_read"].append("docs/api.md")
            scenarios = baseline_evidence["scenarios"]
            assert isinstance(scenarios, list)
            interface = next(item for item in scenarios if item["id"] == "trace-public-interface-change")
            assert isinstance(interface, dict)
            interface["files_read"].append("docs/unrelated.md")
            write_run(root, profile="codex-gpt-5.6", condition="with-r-doc", evidence=with_evidence)
            write_run(root, profile="baseline-no-r-doc", condition="baseline-no-r-doc", evidence=baseline_evidence)
            summary, _ = aggregate_benchmarks.aggregate(CASES, root)
            comparison = summary["paired_comparisons"][0]
            self.assertEqual(comparison["agent"], "Codex")
            self.assertEqual(comparison["model"], "gpt-5.6")
            self.assertEqual(comparison["paired_run_count"], 1)
            self.assertEqual(comparison["conditions"]["with-r-doc"]["unnecessary_reads_average"], 0.0)
            self.assertEqual(comparison["delta"]["unnecessary_reads"], -1.0)
            self.assertFalse(comparison["statistical_readiness"])

    def test_small_audit_performance_fixture_is_clean(self) -> None:
        result = benchmark_audit.measure_size(3, iterations=1, warmup=0)
        self.assertEqual(result["findings"], 0)
        self.assertEqual(len(result["durations_seconds"]), 1)
        self.assertEqual(result["p95_sample_size"], 1)
        self.assertTrue(result["p95_is_low_sample"])
        self.assertEqual(result["max_seconds"], result["p95_seconds"])
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
