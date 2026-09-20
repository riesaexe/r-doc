from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "benchmarks" / "naturalistic"))
sys.path.insert(0, str(Path(__file__).parent))

import export_public_evidence
from test_naturalistic_grader import TASK_PATH, write_run


class NaturalisticExportTests(unittest.TestCase):
    def test_export_preserves_review_events_and_redacts_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_run(
                root,
                profile="codex-gpt-5.5",
                run_id="run-001",
                condition="with-r-doc",
            )
            run_dir = root / "codex-gpt-5.5" / "run-001"
            result = export_public_evidence.grader.grade(TASK_PATH, run_dir)
            (run_dir / "result.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            output = root / "public-evidence.json"
            payload = export_public_evidence.export_manifest(root, output)
            serialized = output.read_text(encoding="utf-8")
            user_path_markers = (
                "C:" + "/" + "Users" + "/",
                "C:" + chr(92) + "Users" + chr(92),
            )
            self.assertEqual(payload["run_count"], 1)
            for marker in user_path_markers:
                self.assertNotIn(marker, serialized)
            self.assertEqual(len(payload["runs"][0]["critical_events"]), 6)
            self.assertEqual(payload["runs"][0]["source_artifact_hashes"]["schema_version"], 2)
            self.assertEqual(payload["runs"][0]["activation_evidence"]["use"]["status"], "observed")


if __name__ == "__main__":
    unittest.main()
