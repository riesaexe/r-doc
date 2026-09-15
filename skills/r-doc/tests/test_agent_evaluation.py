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
                "files_read": list(case["required_files_read"]),
                "files_written": ["evaluation-result.json"],
                "commands": [{"name": command, "exit_code": 0} for command in case["required_commands"]],
                "governance_report": "Captured report",
                "final_diff": "Captured diff",
                "criteria": {dimension: "pass" for dimension in CASES["dimensions"]},
            }
        )
    return {
        "schema_version": 1,
        "skill_version": CASES["skill_version"],
        "agent": "test-agent",
        "scenarios": scenarios,
    }


class AgentEvaluationTests(unittest.TestCase):
    def test_complete_evidence_passes(self) -> None:
        result = evaluate_agent.evaluate(CASES, complete_evidence())
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["percentage"], 100.0)

    def test_missing_criterion_is_rejected(self) -> None:
        evidence = complete_evidence()
        scenarios = evidence["scenarios"]
        assert isinstance(scenarios, list)
        criteria = scenarios[0]["criteria"]
        assert isinstance(criteria, dict)
        criteria.pop("safety")
        result = evaluate_agent.evaluate(CASES, evidence)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("criterion safety" in error for error in result["errors"]))

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
