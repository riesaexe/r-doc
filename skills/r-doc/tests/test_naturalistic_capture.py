from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

NATURALISTIC_ROOT = Path(__file__).parents[3] / "benchmarks" / "naturalistic"
sys.path.insert(0, str(NATURALISTIC_ROOT))

import capture_codex
import grader


PROJECT_ROOT = Path(__file__).parents[3]
TASK_PATH = PROJECT_ROOT / "benchmarks" / "naturalistic" / "tasks" / "api-response-field-rename.json"


class NaturalisticCaptureTests(unittest.TestCase):
    def test_capture_builds_snapshot_normalizes_raw_trace_and_grades_it(self) -> None:
        real_run = subprocess.run

        def fake_codex(command: list[str], **kwargs: object) -> object:
            if command[0] != "codex":
                return real_run(command, **kwargs)
            workspace = Path(command[command.index("-C") + 1])
            (workspace / "src/handler.py").write_text(
                "def serialize_user(user):\n    return {'display_name': user.name}\n",
                encoding="utf-8",
            )
            (workspace / "docs/api.md").write_text(
                "The response contains `display_name`.\n",
                encoding="utf-8",
            )
            (workspace / "tests/test_api.py").write_text(
                "from types import SimpleNamespace\n\n"
                "from src.handler import serialize_user\n\n\n"
                "def test_response_field():\n"
                "    assert serialize_user(SimpleNamespace(name='Ada')) == {'display_name': 'Ada'}\n",
                encoding="utf-8",
            )
            output_path = Path(command[command.index("-o") + 1])
            output_path.write_text(
                f"Finished the task: {workspace / 'src/handler.py'}\n",
                encoding="utf-8",
            )
            raw = {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "python -m pytest tests/test_api.py",
                    "exit_code": 0,
                },
            }
            change = {
                "type": "item.completed",
                "item": {
                    "type": "file_change",
                    "changes": [{"path": str(workspace / "src/handler.py")}],
                },
            }
            return capture_codex.subprocess.CompletedProcess(
                command,
                0,
                json.dumps(raw) + "\n" + json.dumps(change) + "\n",
                "",
            )

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(capture_codex.subprocess, "run", side_effect=fake_codex):
                run_dir, result = capture_codex.capture_run(
                    project_root=PROJECT_ROOT,
                    task_path=TASK_PATH,
                    benchmarks_root=Path(directory),
                    profile="codex-gpt-5.5",
                    run_id="run-001",
                    condition="with-r-doc",
                    model="gpt-5.5",
                    timeout=30,
                )
            self.assertEqual(result["status"], "pass")
            self.assertTrue((run_dir / "artifact-hashes.json").is_file())
            snapshot = json.loads((run_dir / "final-state.json").read_text(encoding="utf-8"))
            self.assertEqual(snapshot["source"], grader.NATURALISTIC_FINAL_STATE_PROVENANCE)
            self.assertIn("display_name", snapshot["files"]["src/handler.py"])
            self.assertNotIn(
                "rdoc-naturalistic",
                (run_dir / "final-response.md").read_text(encoding="utf-8"),
            )
            events = [json.loads(line) for line in (run_dir / "trace.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(events[0]["event"], "prompt")
            self.assertEqual(events[0]["text"], json.loads(TASK_PATH.read_text(encoding="utf-8"))["user_prompt"])
            self.assertTrue(any(event["event"] == "command" for event in events))
            self.assertTrue(any(event["event"] == "file_written" for event in events))

    def test_all_naturalistic_prompts_are_free_of_protocol_markers(self) -> None:
        for task_path in sorted((PROJECT_ROOT / "benchmarks" / "naturalistic" / "tasks").glob("*.json")):
            task = json.loads(task_path.read_text(encoding="utf-8"))
            prompt = task["user_prompt"].casefold()
            for marker in task["prompt_forbidden_markers"]:
                self.assertNotIn(marker.casefold(), prompt, task_path.name)

    def test_recursive_search_marks_all_fixture_candidates_as_read(self) -> None:
        workspace = Path("C:/fixture")
        candidates = {".env", "secrets.md", "src/handler.py"}
        self.assertEqual(
            capture_codex._read_paths_from_command("rg -n user_name .", workspace, candidates),
            sorted(candidates),
        )

    def test_json_escaped_workspace_paths_are_sanitized(self) -> None:
        workspace = Path(r"C:\rdoc-naturalistic-test")
        task = {"fixture_files": {}, "forbidden_reads": []}
        escaped = json.dumps({"path": str(workspace)})
        sanitized = capture_codex._sanitized_text(escaped, workspace, task)
        self.assertNotIn("rdoc-naturalistic", sanitized)


if __name__ == "__main__":
    unittest.main()
