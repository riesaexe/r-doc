from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "benchmarks" / "naturalistic"))

import grader


TASK_PATH = Path(__file__).parents[3] / "benchmarks" / "naturalistic" / "tasks" / "api-response-field-rename.json"


def _write_hashes(run_dir: Path, manifest: dict[str, object], *, mismatch: bool = False) -> None:
    paths = {
        "run.json",
        str(manifest["trace_path"]),
        str(manifest["raw_trace_path"]),
        str(manifest["final_state_path"]),
        str(manifest["final_response_path"]),
    }
    hashes = {
        path: hashlib.sha256((run_dir / path).read_bytes()).hexdigest()
        for path in sorted(paths)
    }
    if mismatch:
        hashes["final-state.json"] = "0" * 64
    (run_dir / "artifact-hashes.json").write_text(
        json.dumps({"schema_version": 1, "algorithm": "sha256", "artifacts": hashes}),
        encoding="utf-8",
    )


def write_run(
    root: Path,
    *,
    profile: str = "codex-gpt-5.5",
    run_id: str = "run-001",
    condition: str = "with-r-doc",
    forbidden_read: bool = False,
    stale_state: bool = False,
    broken_runtime: bool = False,
    hash_mismatch: bool = False,
) -> Path:
    task = json.loads(TASK_PATH.read_text(encoding="utf-8"))
    run_dir = root / profile / run_id
    run_dir.mkdir(parents=True)
    manifest = {
        "schema_version": 2,
        "profile": profile,
        "run_id": run_id,
        "condition": condition,
        "benchmark_kind": "naturalistic-effectiveness",
        "prompt_contract": "naturalistic-user-task",
        "activation_ground_truth": "independent-task-spec",
        "grader_kind": "independent-grader",
        "review_provenance": "independent-grader",
        "capture_source": "naturalistic-capture-runner",
        "final_state_provenance": "runner-generated-from-workspace",
        "trace_provenance": "runner-normalized-raw-cli",
        "task_id": task["task_id"],
        "agent": "Codex",
        "model": "gpt-5.5",
        "agent_exit_code": 0,
        "trace_path": "trace.jsonl",
        "raw_trace_path": "codex-events.jsonl",
        "final_state_path": "final-state.json",
        "final_response_path": "final-response.md",
        "hashes_path": "artifact-hashes.json",
    }
    (run_dir / "run.json").write_text(json.dumps(manifest), encoding="utf-8")

    if stale_state:
        handler = "def serialize_user(user):\n    return {'user_name': user.name}\n"
        docs = "The response contains `user_name`.\n"
        tests = (
            "from types import SimpleNamespace\n\n"
            "from src.handler import serialize_user\n\n\n"
            "def test_response_field():\n"
            "    assert serialize_user(SimpleNamespace(name='Ada')) == {'user_name': 'Ada'}\n"
        )
    elif broken_runtime:
        handler = "# display_name\ndef serialize_user(user):\n    return {}\n"
        docs = "The response contains `display_name`.\n"
        tests = "# display_name\n\ndef test_placeholder():\n    assert True\n"
    else:
        handler = "def serialize_user(user):\n    return {'display_name': user.name}\n"
        docs = "The response contains `display_name`.\n"
        tests = (
            "from types import SimpleNamespace\n\n"
            "from src.handler import serialize_user\n\n\n"
            "def test_response_field():\n"
            "    assert serialize_user(SimpleNamespace(name='Ada')) == {'display_name': 'Ada'}\n"
        )
    final_state = {
        "schema_version": 2,
        "source": "runner-generated-from-workspace",
        "files": {
            "src/handler.py": handler,
            "docs/api.md": docs,
            "tests/test_api.py": tests,
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
    (run_dir / "codex-events.jsonl").write_text("", encoding="utf-8")
    (run_dir / "final-response.md").write_text("Updated the project files.\n", encoding="utf-8")
    _write_hashes(run_dir, manifest, mismatch=hash_mismatch)
    return run_dir


class NaturalisticGraderTests(unittest.TestCase):
    def test_independent_grader_scores_final_state_without_agent_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = grader.grade(TASK_PATH, write_run(Path(directory)))
            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["metrics"]["task_success"], 100.0)
            self.assertEqual(result["metrics"]["executable_outcome"], 100.0)
            self.assertFalse(result["agent_review_used"])

    def test_final_state_failure_is_independent_of_trace_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = grader.grade(TASK_PATH, write_run(Path(directory), stale_state=True))
            self.assertEqual(result["status"], "fail")
            self.assertEqual(result["metrics"]["outcome_compliance"], 0.0)

    def test_executable_outcome_rejects_a_string_passing_but_broken_serializer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = grader.grade(TASK_PATH, write_run(Path(directory), broken_runtime=True))
            self.assertEqual(result["status"], "fail")
            self.assertEqual(result["metrics"]["outcome_compliance"], 100.0)
            self.assertEqual(result["metrics"]["executable_outcome"], 0.0)

    def test_forbidden_reads_fail_independent_grader(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = grader.grade(TASK_PATH, write_run(Path(directory), forbidden_read=True))
            self.assertEqual(result["status"], "fail")
            self.assertEqual(result["metrics"]["context_safety"], 0.0)

    def test_windows_dot_path_cannot_bypass_forbidden_read_match(self) -> None:
        self.assertIsNone(grader._safe_relative(".\\env"))
        self.assertEqual(grader._safe_relative("src\\handler.py"), "src/handler.py")

    def test_artifact_hash_mismatch_fails_independent_grader(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = grader.grade(TASK_PATH, write_run(Path(directory), hash_mismatch=True))
            self.assertEqual(result["status"], "fail")
            self.assertTrue(any("artifact hash mismatch" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
