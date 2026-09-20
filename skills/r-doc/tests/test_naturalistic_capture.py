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
            self.assertIn(capture_codex.RUNNER_PREFLIGHT, command[-1])
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
                "usage": {
                    "input_tokens": 12,
                    "output_tokens": 7,
                    "total_tokens": 19,
                },
                "item": {
                    "type": "error",
                    "message": "Skill descriptions were shortened to fit the skills context budget. Codex can still see every skill, but some descriptions are shorter.",
                },
            }
            skill_read = {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "Get-Content .agents/skills/r-doc/SKILL.md",
                    "aggregated_output": "name: r-doc",
                    "exit_code": 0,
                },
            }
            skill_use = {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "python .agents/skills/r-doc/scripts/audit_docs.py --root .",
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
                "\n".join(json.dumps(item) for item in (raw, skill_read, skill_use, change)) + "\n",
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
            self.assertTrue(result["activation_verified"])
            self.assertTrue((run_dir / "artifact-hashes.json").is_file())
            manifest = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["runner_preflight"], capture_codex.RUNNER_PREFLIGHT_VERSION)
            self.assertEqual(manifest["activation_evidence"]["use"]["status"], "observed")
            self.assertGreaterEqual(manifest["capture_metrics"]["duration_seconds"], 0)
            self.assertEqual(manifest["capture_metrics"]["usage"]["status"], "observed")
            self.assertEqual(manifest["capture_metrics"]["usage"]["fields"]["total_tokens"], 19)
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

    def test_event_v2_contract_keeps_input_name_and_renames_only_payload_key(self) -> None:
        task_path = PROJECT_ROOT / "benchmarks" / "naturalistic" / "tasks" / "event-payload-rename-v2.json"
        task = json.loads(task_path.read_text(encoding="utf-8"))
        self.assertIn("user.name", task["user_prompt"])
        runtime_check = next(
            check for check in task["executable_checks"] if check["id"] == "event-runtime-contract"
        )
        self.assertEqual(runtime_check["args"], [{"name": "Ada"}])
        self.assertEqual(
            runtime_check["expected_return"],
            {"type": "user.created", "payload": {"display_name": "Ada"}},
        )

    def test_runner_preflight_is_generic_and_separate_from_task_prompt(self) -> None:
        task_prompt = "Synchronize the implementation and documentation."
        prompt = capture_codex._runner_prompt(task_prompt)
        self.assertIn(capture_codex.RUNNER_PREFLIGHT, prompt)
        self.assertIn("User task:\n" + task_prompt, prompt)
        self.assertNotIn("r-doc", capture_codex.RUNNER_PREFLIGHT.casefold())
        self.assertNotIn("benchmark", capture_codex.RUNNER_PREFLIGHT.casefold())
        for boundary in (".env", ".env.*", "secrets.*", "rg --hidden", "src", "docs", "tests"):
            self.assertIn(boundary, capture_codex.RUNNER_PREFLIGHT)

    def test_recursive_search_respects_hidden_file_and_content_search_semantics(self) -> None:
        workspace = Path("C:/fixture")
        candidates = {".env", "secrets.md", "src/handler.py"}
        self.assertEqual(
            capture_codex._read_paths_from_command("rg -n user_name .", workspace, candidates),
            ["secrets.md", "src/handler.py"],
        )
        self.assertEqual(
            capture_codex._read_paths_from_command("rg --hidden -n user_name .", workspace, candidates),
            sorted(candidates),
        )
        excluded = capture_codex._read_paths_from_command(
            "rg --hidden -n --glob '!*.env*' --glob '!secrets.md' user_name .",
            workspace,
            candidates,
        )
        self.assertNotIn(".env", excluded)
        self.assertNotIn("secrets.md", excluded)
        self.assertIn("src/handler.py", excluded)
        self.assertEqual(
            capture_codex._rg_excluded_candidates(
                ["--glob", "", "!**/.env*", "--glob", "", "!**/*secret*"],
                candidates,
            ),
            {".env", "secrets.md"},
        )
        powershell_wrapped = (
            r'''pwsh -Command "rg -n -i --glob '"'!*.env'"' --glob '"'!secrets.md'"' '''
            r'''"user_name|display_name" src\repository.py docs\database.md tests\test_repository.py"'''
        )
        self.assertEqual(
            capture_codex._read_paths_from_command(
                powershell_wrapped,
                workspace,
                {".env", "secrets.md", "src/repository.py", "docs/database.md", "tests/test_repository.py"},
            ),
            ["docs/database.md", "src/repository.py", "tests/test_repository.py"],
        )
        self.assertEqual(
            capture_codex._read_paths_from_command("rg --files .", workspace, candidates),
            [],
        )
        self.assertEqual(
            capture_codex._read_paths_from_command("Get-ChildItem -Recurse .", workspace, candidates),
            [],
        )
        self.assertEqual(
            capture_codex._read_paths_from_command(
                "Get-ChildItem -Force . | Where-Object { $_.Name -notmatch '^\\.env' } | "
                "Select-Object Mode,Length,LastWriteTime,Name -PathType Container",
                workspace,
                candidates,
            ),
            [],
        )
        self.assertEqual(
            capture_codex._read_paths_from_command(
                "Get-Content -Raw docs/architecture.md; "
                "Write-Output '.env'; Write-Output 'secrets.md'",
                workspace,
                {".env", "secrets.md", "docs/architecture.md"},
            ),
            ["docs/architecture.md"],
        )
        self.assertEqual(
            capture_codex._read_paths_from_command(
                "Get-ChildItem -Recurse .; Get-Content src/handler.py",
                workspace,
                candidates,
            ),
            ["src/handler.py"],
        )
        self.assertEqual(
            capture_codex._read_paths_from_command("git status --short", workspace, candidates),
            [],
        )

    def test_with_r_doc_is_installed_in_workspace_and_isolated_user_home(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            isolated_home = Path(directory) / "home"
            capture_codex._install_skill(
                PROJECT_ROOT,
                workspace,
                "with-r-doc",
                isolated_home=isolated_home,
            )
            self.assertTrue((workspace / ".agents/skills/r-doc/SKILL.md").is_file())
            self.assertTrue((isolated_home / ".agents/skills/r-doc/SKILL.md").is_file())

    def test_bounded_protected_search_is_a_r_doc_use_signal(self) -> None:
        safe_command = "rg -n --glob '!**/.env*' --glob '!**/*secret*' term src tests docs"
        broad_command = "rg --hidden -n term ."
        self.assertTrue(capture_codex._bounded_read_policy_signal(safe_command))
        self.assertFalse(capture_codex._bounded_read_policy_signal(broad_command))

    def test_bounded_project_reads_are_a_r_doc_use_signal(self) -> None:
        self.assertTrue(capture_codex._bounded_project_read_signal("Get-Content -Raw src/events.py"))
        self.assertTrue(capture_codex._bounded_project_read_signal("rg -n user_name src docs tests"))
        self.assertFalse(capture_codex._bounded_project_read_signal("rg -n user_name ."))
        self.assertFalse(capture_codex._bounded_project_read_signal("Get-Content -Recurse src"))

    def test_skill_use_signal_requires_a_read_after_skill_load(self) -> None:
        events = [
            {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "rg -n user_name .",
                    "exit_code": 0,
                },
            },
            {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "Get-Content .agents/skills/r-doc/SKILL.md",
                    "aggregated_output": "name: r-doc",
                    "exit_code": 0,
                },
            },
            {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "Get-Content -Raw src/events.py",
                    "exit_code": 0,
                },
            },
        ]
        evidence = capture_codex._activation_evidence(
            "\n".join(json.dumps(event) for event in events),
            "",
            "with-r-doc",
        )
        self.assertEqual(evidence["use"]["status"], "observed")
        self.assertIn("raw_event_rdoc_bounded_project_read", evidence["use"]["signals"])

        evidence_without_post_load_read = capture_codex._activation_evidence(
            "\n".join(json.dumps(event) for event in events[:2]),
            "",
            "with-r-doc",
        )
        self.assertEqual(evidence_without_post_load_read["use"]["status"], "not_observed")

    def test_json_escaped_workspace_paths_are_sanitized(self) -> None:
        workspace = Path(r"C:\rdoc-naturalistic-test")
        task = {"fixture_files": {}, "forbidden_reads": []}
        escaped = json.dumps({"path": str(workspace)})
        sanitized = capture_codex._sanitized_text(escaped, workspace, task)
        self.assertNotIn("rdoc-naturalistic", sanitized)


if __name__ == "__main__":
    unittest.main()
