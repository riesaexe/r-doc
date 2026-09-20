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
CLI_TASK_PATH = Path(__file__).parents[3] / "benchmarks" / "naturalistic" / "tasks" / "cli-option-rename.json"
EVENT_TASK_PATH = Path(__file__).parents[3] / "benchmarks" / "naturalistic" / "tasks" / "event-payload-rename-v2.json"
CROSS_TASK_PATH = Path(__file__).parents[3] / "benchmarks" / "naturalistic" / "tasks" / "cross-module-contract-migration-v1.json"


def _write_hashes(run_dir: Path, manifest: dict[str, object], *, mismatch: bool = False) -> None:
    paths = {
        "run.json",
        str(manifest["trace_path"]),
        str(manifest["raw_trace_path"]),
        str(manifest["final_state_path"]),
        str(manifest["final_response_path"]),
    }
    hashes = {
        path: {
            "sha256": grader._sha256_lf(run_dir / path),
            "canonicalization": grader.HASH_CANONICALIZATION,
        }
        for path in sorted(paths)
    }
    if mismatch:
        hashes["final-state.json"] = {
            "sha256": "0" * 64,
            "canonicalization": grader.HASH_CANONICALIZATION,
        }
    (run_dir / "artifact-hashes.json").write_text(
        json.dumps(
            {
                "schema_version": grader.HASH_SCHEMA_VERSION,
                "algorithm": "sha256",
                "canonicalization": grader.HASH_CANONICALIZATION,
                "artifacts": hashes,
            }
        ),
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
    task_path: Path = TASK_PATH,
    final_files: dict[str, str] | None = None,
    model: str = "gpt-5.5",
) -> Path:
    task = json.loads(task_path.read_text(encoding="utf-8"))
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
        "activation_evidence": {
            "schema_version": grader.ACTIVATION_EVIDENCE_SCHEMA_VERSION,
            "skill": "r-doc",
            "visibility": {
                "status": "not_applicable" if condition == "baseline-no-r-doc" else "confirmed",
                "signals": ["test-fixture"],
            },
            "load": {
                "status": "not_applicable" if condition == "baseline-no-r-doc" else "observed",
                "signals": ["test-fixture"],
            },
            "use": {
                "status": "not_applicable" if condition == "baseline-no-r-doc" else "observed",
                "signals": ["test-fixture"],
            },
            "limitation": "test fixture",
        },
        "task_id": task["task_id"],
        "agent": "Codex",
        "model": model,
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
    files = final_files or {
        "src/handler.py": handler,
        "docs/api.md": docs,
        "tests/test_api.py": tests,
    }
    final_state = {
        "schema_version": 2,
        "source": "runner-generated-from-workspace",
        "files": files,
    }
    (run_dir / "final-state.json").write_text(json.dumps(final_state), encoding="utf-8")
    file_paths = list(files)
    events = [
        {"sequence": 0, "event": "prompt", "text": task["user_prompt"]},
        {"sequence": 1, "event": "file_read", "path": file_paths[0]},
        *[
            {"sequence": index + 2, "event": "file_written", "path": path}
            for index, path in enumerate(file_paths)
        ],
        {
            "sequence": len(file_paths) + 2,
            "event": "command",
            "name": "pytest",
            "command": "pytest",
            "exit_code": 0,
        },
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

    def test_unverified_activation_does_not_hide_a_successful_task_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = write_run(Path(directory))
            manifest_path = run_dir / "run.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["activation_evidence"]["use"]["status"] = "not_observed"
            manifest["activation_evidence"]["use"]["signals"] = []
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            _write_hashes(run_dir, manifest)
            result = grader.grade(TASK_PATH, run_dir)
            self.assertEqual(result["status"], "fail")
            self.assertEqual(result["task_outcome_status"], "pass")
            self.assertEqual(result["metrics"]["task_success"], 100.0)
            self.assertEqual(result["metrics"]["context_safety"], 100.0)

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

    def test_cli_negative_option_test_is_not_rejected_by_static_assertion(self) -> None:
        files = {
            "src/__init__.py": "",
            "src/cli.py": (
                "import argparse\n\n"
                "def parse_args(argv=None):\n"
                "    parser = argparse.ArgumentParser()\n"
                "    parser.add_argument('--display-name', required=True)\n"
                "    return parser.parse_args(argv)\n"
            ),
            "docs/cli.md": "# CLI\n\nUse `--display-name <name>` to select a user.\n",
            "tests/test_cli.py": (
                "import pytest\n\n"
                "from src.cli import parse_args\n\n\n"
                "def test_display_name_option():\n"
                "    assert parse_args(['--display-name', 'Ada']).display_name == 'Ada'\n\n\n"
                "def test_user_name_option_is_not_supported():\n"
                "    with pytest.raises(SystemExit):\n"
                "        parse_args(['--user-name', 'Ada'])\n"
            ),
        }
        with tempfile.TemporaryDirectory() as directory:
            result = grader.grade(
                CLI_TASK_PATH,
                write_run(
                    Path(directory),
                    task_path=CLI_TASK_PATH,
                    final_files=files,
                ),
            )
            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["metrics"]["outcome_compliance"], 100.0)
            self.assertEqual(result["metrics"]["executable_outcome"], 100.0)

    def test_event_absence_assertion_is_not_rejected_by_static_assertion(self) -> None:
        files = {
            "src/__init__.py": "",
            "src/events.py": (
                "def user_created_event(user):\n"
                "    return {'type': 'user.created', 'payload': {'display_name': user.name}}\n"
            ),
            "docs/events.md": "# User-created event\n\nThe payload contains `display_name`.\n",
            "tests/test_events.py": (
                "from types import SimpleNamespace\n\n"
                "from src.events import user_created_event\n\n\n"
                "def test_user_created_event():\n"
                "    event = user_created_event(SimpleNamespace(name='Ada'))\n"
                "    assert event['payload']['display_name'] == 'Ada'\n"
                "    assert 'user_name' not in event['payload']\n"
            ),
        }
        with tempfile.TemporaryDirectory() as directory:
            result = grader.grade(
                EVENT_TASK_PATH,
                write_run(
                    Path(directory),
                    task_path=EVENT_TASK_PATH,
                    final_files=files,
                ),
            )
            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["metrics"]["outcome_compliance"], 100.0)
            self.assertEqual(result["metrics"]["executable_outcome"], 100.0)

    def test_callable_check_supports_explicit_mapping_arguments(self) -> None:
        task = {
            "executable_checks": [
                {
                    "id": "producer",
                    "kind": "callable_return",
                    "module_path": "src/producer.py",
                    "callable": "make_user_event",
                    "argument_mode": "mapping",
                    "args": [{"id": "u-1"}],
                    "expected_return": {"user_id": "u-1"},
                    "forbidden_keys": ["id"],
                },
                {
                    "id": "consumer",
                    "kind": "callable_return",
                    "module_path": "src/consumer.py",
                    "callable": "display_user",
                    "argument_mode": "mapping",
                    "args": [{"user_id": "u-1"}],
                    "expected_return": "u-1",
                    "forbidden_keys": [],
                },
            ]
        }
        files = {
            "src/producer.py": "def make_user_event(user):\n    return {'user_id': user['id']}\n",
            "src/consumer.py": "def display_user(event):\n    return event['user_id']\n",
        }
        results = grader._run_executable_checks(task, files)
        self.assertEqual([item["status"] for item in results], ["pass", "pass"])

    def test_natural_language_text_assertions_normalize_case_and_dashes(self) -> None:
        task = {
            "executable_checks": [
                {
                    "id": "docs",
                    "kind": "text_assertions",
                    "path": "docs/release.md",
                    "match": "natural-language",
                    "contains": ["30 second"],
                    "contains_any": [["verification", "verify", "confirm"]],
                    "not_contains": ["10 second"],
                }
            ]
        }
        passing = grader._run_executable_checks(
            task,
            {"docs/release.md": "The current 30-second policy is ready. Confirm the release steps."},
        )
        self.assertEqual(passing[0]["status"], "pass")

        failing = grader._run_executable_checks(
            task,
            {"docs/release.md": "The current 30-second policy replaced the 10-second policy."},
        )
        self.assertEqual(failing[0]["status"], "fail")
        self.assertIn("still contains '10 second'", failing[0]["details"])

    def test_final_state_uses_natural_language_assertion_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = json.loads(TASK_PATH.read_text(encoding="utf-8"))
            task["assertions"] = {
                "docs/api.md": {
                    "match": "natural-language",
                    "contains": ["30 second"],
                    "contains_any": [["verification", "confirm"]],
                }
            }
            task_path = root / "task.json"
            task_path.write_text(json.dumps(task), encoding="utf-8")
            files = {
                "src/handler.py": "def serialize_user(user):\n    return {'display_name': user.name}\n",
                "docs/api.md": "The current 30-second contract exposes `display_name`. Confirm the verification steps.\n",
                "tests/test_api.py": (
                    "from types import SimpleNamespace\n\n"
                    "from src.handler import serialize_user\n\n\n"
                    "def test_response_field():\n"
                    "    assert serialize_user(SimpleNamespace(name='Ada')) == {'display_name': 'Ada'}\n"
                ),
            }
            result = grader.grade(
                task_path,
                write_run(root, task_path=task_path, final_files=files),
            )
            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["metrics"]["outcome_compliance"], 100.0)

    def test_cross_module_task_uses_mapping_runtime_contract(self) -> None:
        task = json.loads(CROSS_TASK_PATH.read_text(encoding="utf-8"))
        files = {
            "src/__init__.py": "",
            "src/producer.py": "def make_user_event(user):\n    return {'user_id': user['id']}\n",
            "src/consumer.py": "def display_user(event):\n    return event['user_id']\n",
            "tests/test_contract.py": (
                "from src.consumer import display_user\n"
                "from src.producer import make_user_event\n\n\n"
                "def test_contract():\n"
                "    event = make_user_event({'id': 'u-1'})\n"
                "    assert display_user(event) == 'u-1'\n"
                "    assert event['user_id'] == 'u-1'\n"
            ),
        }
        results = grader._run_executable_checks(task, files)
        self.assertEqual([item["status"] for item in results], ["pass", "pass", "pass"])

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

    def test_artifact_hashes_tolerate_lf_checkout_of_windows_capture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = write_run(Path(directory))
            manifest = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
            _write_hashes(run_dir, manifest)
            for path in {
                "run.json",
                str(manifest["trace_path"]),
                str(manifest["raw_trace_path"]),
                str(manifest["final_state_path"]),
                str(manifest["final_response_path"]),
            }:
                artifact = run_dir / path
                artifact.write_bytes(artifact.read_bytes().replace(b"\r\n", b"\n"))
            result = grader.grade(TASK_PATH, run_dir)
            self.assertEqual(result["status"], "pass")
            self.assertEqual(
                next(check for check in result["checks"] if check["id"] == "artifact_integrity")["status"],
                "pass",
            )


if __name__ == "__main__":
    unittest.main()
