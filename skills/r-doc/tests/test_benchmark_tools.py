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
    schema_version = 2
    events: list[dict[str, object]] = [
        {
            "schema_version": schema_version,
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
        events.append({"schema_version": schema_version, "sequence": sequence, "event": "scenario_start", "scenario_id": identifier})
        sequence += 1
        events.append(
            {"schema_version": schema_version, "sequence": sequence, "event": "prompt", "scenario_id": identifier, "text": scenario["prompt"]}
        )
        sequence += 1
        events.append(
            {
                "schema_version": schema_version,
                "sequence": sequence,
                "event": "activation_decision",
                "scenario_id": identifier,
                "decision": scenario["activation"],
            }
        )
        sequence += 1
        events.append(
            {
                "schema_version": schema_version,
                "sequence": sequence,
                "event": "skill_selected",
                "scenario_id": identifier,
                "skill": (
                    "r-doc"
                    if manifest["condition"] == "with-r-doc" and scenario["activation"] == "activated"
                    else "none"
                ),
            }
        )
        sequence += 1
        for path in scenario["paths_checked"]:
            events.append(
                {"schema_version": schema_version, "sequence": sequence, "event": "path_checked", "scenario_id": identifier, "path": path}
            )
            sequence += 1
        for path in scenario["files_read"]:
            events.append(
                {"schema_version": schema_version, "sequence": sequence, "event": "file_read", "scenario_id": identifier, "path": path}
            )
            sequence += 1
        for command in scenario["commands"]:
            assert isinstance(command, dict)
            event: dict[str, object] = {
                "schema_version": schema_version,
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
                {"schema_version": schema_version, "sequence": sequence, "event": "file_written", "scenario_id": identifier, "path": path}
            )
            sequence += 1
        for event_name, field in (
            ("governance_report", "governance_report"),
            ("final_response", "final_response"),
            ("diff_snapshot", "final_diff"),
        ):
            events.append(
                {
                    "schema_version": schema_version,
                    "sequence": sequence,
                    "event": event_name,
                    "scenario_id": identifier,
                    "text": scenario[field],
                }
            )
            sequence += 1
        for dimension, assessment in scenario["review"].items():
            events.append(
                {
                    "schema_version": schema_version,
                    "sequence": sequence,
                    "event": "review",
                    "scenario_id": identifier,
                    "dimension": dimension,
                    "status": assessment["status"],
                    "basis": assessment["basis"],
                }
            )
            sequence += 1
        events.append({"schema_version": schema_version, "sequence": sequence, "event": "scenario_end", "scenario_id": identifier})
        sequence += 1
    events.append({"schema_version": schema_version, "sequence": sequence, "event": "trace_end"})
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
    else:
        evidence = json.loads(json.dumps(evidence))
    evidence["condition"] = condition
    scenarios = evidence["scenarios"]
    assert isinstance(scenarios, list)
    for scenario in scenarios:
        assert isinstance(scenario, dict)
        scenario["skill_selected"] = (
            "r-doc" if condition == "with-r-doc" and scenario["activation"] == "activated" else "none"
        )
    manifest = {
        "schema_version": 2,
        "profile": profile,
        "run_id": run_id,
        "condition": condition,
        "benchmark_kind": "skill-layer-ablation",
        "prompt_contract": "fixed-protocol",
        "activation_ground_truth": "case-contract",
        "grader_kind": "agent-self-review",
        "review_provenance": "agent-generated",
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

    def test_summary_declares_conformance_and_agent_review_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_run(root)
            summary, _ = aggregate_benchmarks.aggregate(CASES, root)
            self.assertEqual(summary["benchmark_kind"], "skill-layer-ablation")
            self.assertEqual(summary["benchmark_name"], "Conformance Benchmark")
            self.assertEqual(summary["activation_ground_truth"], "case-contract")
            self.assertEqual(summary["grader_kind"], "agent-self-review")
            self.assertEqual(summary["review_provenance"], "agent-generated")
            self.assertIn("not natural activation accuracy", summary["metric_semantics"]["activation_accuracy"])
            self.assertIn("not independently graded", summary["metric_semantics"]["task_success"])

    def test_manifest_requires_benchmark_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir = write_run(root)
            manifest = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
            del manifest["grader_kind"]
            (run_dir / "run.json").write_text(json.dumps(manifest), encoding="utf-8")
            summary, _ = aggregate_benchmarks.aggregate(CASES, root)
            self.assertEqual(summary["status"], "fail")
            self.assertTrue(any("run.json is missing grader_kind" in error for error in summary["errors"]))

    def test_conformance_aggregator_rejects_a_naturalistic_layer_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir = write_run(root)
            manifest = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
            manifest["benchmark_kind"] = "naturalistic-effectiveness"
            (run_dir / "run.json").write_text(json.dumps(manifest), encoding="utf-8")
            summary, result_files = aggregate_benchmarks.aggregate(CASES, root)
            self.assertEqual(summary["status"], "fail")
            self.assertEqual(summary["profiles"], {})
            self.assertEqual(summary["paired_comparisons"], [])
            self.assertEqual(result_files, [])
            self.assertTrue(any("rejects non-conformance benchmark_kind" in error for error in summary["errors"]))

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

    def test_failed_evaluator_run_is_retained_but_excluded_from_aggregates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = complete_evidence()
            scenarios = evidence["scenarios"]
            assert isinstance(scenarios, list)
            review = scenarios[0]["review"]
            assert isinstance(review, dict)
            context = review["context_economy"]
            assert isinstance(context, dict)
            context["status"] = "fail"
            write_run(root, evidence=evidence)
            summary, _ = aggregate_benchmarks.aggregate(CASES, root)
            self.assertEqual(summary["status"], "fail")
            self.assertEqual(summary["profiles"], {})
            self.assertEqual(summary["paired_comparisons"], [])
            self.assertEqual(summary["runs"][0]["trace_validation"], "pass")
            self.assertEqual(summary["runs"][0]["status"], "fail")

    def test_trace_rejects_undeclared_event_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir = write_run(root)
            lines = (run_dir / "trace.jsonl").read_text(encoding="utf-8").splitlines()
            event = json.loads(lines[0])
            event["note"] = "not part of the trace contract"
            lines[0] = json.dumps(event)
            (run_dir / "trace.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
            summary, _ = aggregate_benchmarks.aggregate(CASES, root)
            self.assertEqual(summary["status"], "fail")
            self.assertTrue(any("unsupported fields: note" in error for error in summary["errors"]))

    def test_trace_proves_text_and_review_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir = write_run(root)
            lines = (run_dir / "trace.jsonl").read_text(encoding="utf-8").splitlines()
            final_response_index = next(index for index, line in enumerate(lines) if '"event": "final_response"' in line)
            event = json.loads(lines[final_response_index])
            event["text"] = "trace response differs from evidence"
            lines[final_response_index] = json.dumps(event)
            (run_dir / "trace.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
            summary, _ = aggregate_benchmarks.aggregate(CASES, root)
            self.assertEqual(summary["status"], "fail")
            self.assertTrue(any("trace/evidence mismatch" in error and "final_response" in error for error in summary["errors"]))

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
            self.assertFalse(comparison["trend_readiness"])
            self.assertFalse(comparison["statistical_readiness"])

    def test_paired_statistics_report_readiness_and_confidence_interval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index in range(1, 6):
                run_id = f"run-{index:03d}"
                with_evidence = complete_evidence()
                baseline_evidence = complete_evidence()
                with_scenarios = with_evidence["scenarios"]
                baseline_scenarios = baseline_evidence["scenarios"]
                assert isinstance(with_scenarios, list)
                assert isinstance(baseline_scenarios, list)
                with_interface = next(item for item in with_scenarios if item["id"] == "trace-public-interface-change")
                baseline_interface = next(item for item in baseline_scenarios if item["id"] == "trace-public-interface-change")
                assert isinstance(with_interface, dict)
                assert isinstance(baseline_interface, dict)
                baseline_interface["files_read"].append("docs/unrelated.md")
                write_run(root, run_id=run_id, condition="with-r-doc", evidence=with_evidence)
                write_run(root, profile="baseline-no-r-doc", run_id=run_id, condition="baseline-no-r-doc", evidence=baseline_evidence)
            summary, _ = aggregate_benchmarks.aggregate(CASES, root)
            comparison = summary["paired_comparisons"][0]
            self.assertTrue(comparison["trend_readiness"])
            self.assertTrue(comparison["statistical_readiness"])
            self.assertFalse(comparison["strong_evidence_readiness"])
            stats = comparison["delta_statistics"]["unnecessary_reads"]
            self.assertEqual(stats["ci95_low"], -1.0)
            self.assertEqual(stats["ci95_high"], -1.0)
            self.assertEqual(stats["ci95_method"], "student-t-95")

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
