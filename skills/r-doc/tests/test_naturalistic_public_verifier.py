from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "benchmarks" / "naturalistic"))
sys.path.insert(0, str(Path(__file__).parent))

import export_public_evidence
import verify_public_evidence
from test_naturalistic_grader import TASK_PATH, write_run


class NaturalisticPublicVerifierTests(unittest.TestCase):
    def test_public_evidence_passes_without_private_source_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_run(root, profile="codex-gpt-5.5", run_id="run-001", condition="with-r-doc")
            run_dir = root / "codex-gpt-5.5" / "run-001"
            result = export_public_evidence.grader.grade(TASK_PATH, run_dir)
            (run_dir / "result.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            public_path = root / "public-evidence.json"
            export_public_evidence.export_manifest(root, public_path)
            report = verify_public_evidence.verify_public_evidence(public_path)
            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["source_artifacts"], "unavailable")

    def test_source_hashes_can_be_replayed_when_source_root_is_available(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_run(root, profile="codex-gpt-5.5", run_id="run-001", condition="with-r-doc")
            run_dir = root / "codex-gpt-5.5" / "run-001"
            (run_dir / "result.json").write_text(
                json.dumps(export_public_evidence.grader.grade(TASK_PATH, run_dir)),
                encoding="utf-8",
            )
            public_path = root / "public-evidence.json"
            export_public_evidence.export_manifest(root, public_path)
            report = verify_public_evidence.verify_public_evidence(
                public_path,
                source_root=root,
            )
            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["source_artifacts"], "verified")

    def test_absolute_run_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_run(root, profile="codex-gpt-5.5", run_id="run-001", condition="with-r-doc")
            run_dir = root / "codex-gpt-5.5" / "run-001"
            (run_dir / "result.json").write_text(
                json.dumps(export_public_evidence.grader.grade(TASK_PATH, run_dir)),
                encoding="utf-8",
            )
            public_path = root / "public-evidence.json"
            export_public_evidence.export_manifest(root, public_path)
            payload = json.loads(public_path.read_text(encoding="utf-8"))
            tampered = copy.deepcopy(payload)
            tampered["runs"][0]["run_dir"] = chr(67) + ":/private/run-001"
            public_path.write_text(json.dumps(tampered), encoding="utf-8")
            report = verify_public_evidence.verify_public_evidence(public_path)
            self.assertEqual(report["status"], "fail")
            self.assertTrue(any("absolute path" in error for error in report["errors"]))

    def test_relative_separator_in_command_is_not_an_absolute_path(self) -> None:
        self.assertIsNone(
            verify_public_evidence.ABSOLUTE_PATH.search(
                "Missing expected text: $($check.Path) / $($check.Pattern)"
            )
        )
        self.assertIsNotNone(
            verify_public_evidence.ABSOLUTE_PATH.search(
                "pwsh -Command C:/fixture/project"
            )
        )


if __name__ == "__main__":
    unittest.main()
