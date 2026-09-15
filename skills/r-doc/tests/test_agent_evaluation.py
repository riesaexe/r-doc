from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import evaluate_agent


CASES = evaluate_agent.load_cases(Path(__file__).parents[1] / "evals" / "cases.json")


def complete_evidence() -> dict[str, object]:
    scenarios: list[dict[str, object]] = []
    for case in CASES["scenarios"]:
        scenarios.append(
            {
                "id": case["id"],
                "activation": case["expected_activation"],
                "prompt": f"Prompt for {case['id']}",
                "paths_checked": list(case["required_paths_checked"]),
                "files_read": list(case["required_files_read"]),
                "files_written": ["evaluation-result.json"],
                "commands": [{"name": command, "exit_code": 0} for command in case["required_command_sequence"]],
                "governance_report": "Captured report",
                "final_diff": "Captured diff",
                "review": {
                    dimension: {"status": "pass", "basis": f"Reviewed {dimension}"}
                    for dimension in CASES["review_dimensions"]
                },
            }
        )
    return {
        "schema_version": 2,
        "skill_version": CASES["skill_version"],
        "agent": "test-agent",
        "scenarios": scenarios,
    }


class AgentEvaluationTests(unittest.TestCase):
    def test_complete_evidence_passes(self) -> None:
        result = evaluate_agent.evaluate(CASES, complete_evidence())
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["percentage"], 100.0)

    def test_missing_review_assessment_is_rejected(self) -> None:
        evidence = complete_evidence()
        scenarios = evidence["scenarios"]
        assert isinstance(scenarios, list)
        review = scenarios[0]["review"]
        assert isinstance(review, dict)
        review.pop("preservation")
        result = evaluate_agent.evaluate(CASES, evidence)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("review preservation" in error for error in result["errors"]))

    def test_sensitive_value_is_rejected_from_evidence(self) -> None:
        evidence = complete_evidence()
        scenarios = evidence["scenarios"]
        assert isinstance(scenarios, list)
        scenarios[0]["governance_report"] = "redacted sk-" + "a" * 24
        result = evaluate_agent.evaluate(CASES, evidence)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("sensitive value" in error for error in result["errors"]))

    def test_skill_version_must_match_cases(self) -> None:
        evidence = complete_evidence()
        evidence.pop("skill_version")
        result = evaluate_agent.evaluate(CASES, evidence)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("skill_version" in error for error in result["errors"]))

        evidence = complete_evidence()
        evidence["skill_version"] = "0.2.8"
        result = evaluate_agent.evaluate(CASES, evidence)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("must match cases" in error for error in result["errors"]))

    def test_failed_required_command_is_rejected(self) -> None:
        evidence = complete_evidence()
        scenarios = evidence["scenarios"]
        assert isinstance(scenarios, list)
        commands = scenarios[0]["commands"]
        assert isinstance(commands, list)
        commands[0]["exit_code"] = 1
        result = evaluate_agent.evaluate(CASES, evidence)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("must exit 0" in error for error in result["errors"]))

    def test_required_commands_must_follow_declared_order(self) -> None:
        evidence = complete_evidence()
        scenarios = evidence["scenarios"]
        assert isinstance(scenarios, list)
        structural = next(item for item in scenarios if item["id"] == "handle-structural-audit-failure")
        structural["commands"] = [
            {"name": "audit_docs.py", "exit_code": 0},
            {"name": "repair_docs.py", "exit_code": 0},
        ]
        result = evaluate_agent.evaluate(CASES, evidence)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("out of order" in error for error in result["errors"]))

    def test_paths_checked_are_separate_from_files_read(self) -> None:
        evidence = complete_evidence()
        scenarios = evidence["scenarios"]
        assert isinstance(scenarios, list)
        initial = next(item for item in scenarios if item["id"] == "initialize-undocumented-project")
        self.assertEqual(initial["files_read"], [])
        self.assertEqual(initial["paths_checked"], ["AGENTS.md", "docs/"])
        result = evaluate_agent.evaluate(CASES, evidence)
        self.assertEqual(result["status"], "pass")
