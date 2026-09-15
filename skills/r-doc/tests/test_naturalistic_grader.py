from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "benchmarks" / "naturalistic"))

import grader


TASK_PATH = Path(__file__).parents[3] / "benchmarks" / "naturalistic" / "tasks" / "api-response-field-rename.json"


def write_run(root: Path, *, forbidden_read: bool = False, stale_state: bool = False) -> Path:
    task = json.loads(TASK_PATH.read_text(encoding="utf-8"))
    run_dir = root / "codex-gpt-5.5" / "run-001"
    run_dir.mkdir(parents=True)
    manifest = {
        "schema_version": 1,
        "profile": "codex-gpt-5.5",
        "run_id": "run-001",
        "condition": "with-r-doc",
        "benchmark_kind": "naturalistic-effectiveness",
        "prompt_contract": "naturalistic-user-task",
        "activation_ground_truth": "independent-task-spec",
        "grader_kind": "independent-grader",
        "review_provenance": "independent-grader",
        "task_id": task["task_id"],
        "agent": "Codex",
        "model": "gpt-5.5",
        "trace_path": "trace.jsonl",
        "final_state_path": "final-state.json",
        "final_response_path": "final-response.md",
    }
    (run_dir / "run.json").write_text(json.dumps(manifest), encoding="utf-8")
    final_value = "user_name" if stale_state else "display_name"
    final_state = {
        "schema_version": 1,
        "files": {
            "src/handler.py": f"return {{'{final_value}': user.name}}\n",
            "docs/api.md": f"The response contains `{final_value}`.\n",
            "tests/test_api.py": f"assert response['{final_value}'] == 'Ada'\n",
        },
    }
    (run_dir / "final-state.json").write_text(json.dumps(final_state), encoding="utf-8")
    events = [
        {"sequence": 0, "event": "prompt", "text": task["user_prompt"]},
        {"sequence": 1, "event": "file_read", "path": "src/handler.py"},
        {"sequence": 2, "event": "file_written", "path": "src/handler.py"},
        {"sequence": 3, "event": "file_written", "path": "docs/api.md"},
        {"sequence": 4, "event": "file_written", "path": "tests/test_api.py"},
        {"sequence": 5, "event": "command", "name": "pytest", "command": "pytest", "exit_code": 0},
    ]
    if forbidden_read:
        events.insert(1, {"sequence": 1, "event": "file_read", "path": ".env"})
        for sequence, event in enumerate(events):
            event["sequence"] = sequence
    (run_dir / "trace.jsonl").write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")
    (run_dir / "final-response.md").write_text("Updated the project files.\n", encoding="utf-8")
    return run_dir


class NaturalisticGraderTests(unittest.TestCase):
    def test_independent_grader_scores_final_state_without_agent_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = grader.grade(TASK_PATH, write_run(Path(directory)))
            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["metrics"]["task_success"], 100.0)
            self.assertFalse(result["agent_review_used"])

    def test_final_state_failure_is_independent_of_trace_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = grader.grade(TASK_PATH, write_run(Path(directory), stale_state=True))
            self.assertEqual(result["status"], "fail")
            self.assertEqual(result["metrics"]["outcome_compliance"], 0.0)

    def test_forbidden_reads_fail_independent_grader(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = grader.grade(TASK_PATH, write_run(Path(directory), forbidden_read=True))
            self.assertEqual(result["status"], "fail")
            self.assertEqual(result["metrics"]["context_safety"], 0.0)


if __name__ == "__main__":
    unittest.main()
