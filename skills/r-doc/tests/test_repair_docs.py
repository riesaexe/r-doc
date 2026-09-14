from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import audit_docs
import repair_docs
from helpers import topic, valid_project, write_file


class RepairDocsTests(unittest.TestCase):
    def test_repair_plan_is_empty_for_valid_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            self.assertEqual(repair_docs.plan_repairs(root), [])

    def test_repair_preview_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            actions = repair_docs.plan_repairs(root)
            self.assertTrue(actions)
            self.assertFalse((root / "AGENTS.md").exists())
            self.assertFalse((root / "docs/README.md").exists())

    def test_repair_apply_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            actions = repair_docs.plan_repairs(root)
            repair_docs.apply_repairs(root, actions)
            self.assertEqual(repair_docs.plan_repairs(root), [])
            self.assertEqual([item.code for item in audit_docs.audit(root)], [])

    def test_repair_adds_an_unindexed_document_link(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, "docs/guide/new.md", topic("DOC-002", "New topic"))
            actions = repair_docs.plan_repairs(root)
            self.assertEqual(len(actions), 1)
            repair_docs.apply_repairs(root, actions)
            self.assertIn("[New topic](new.md)", (root / "docs/guide/README.md").read_text(encoding="utf-8"))

    def test_repair_creates_nested_index_and_parent_link(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_file(root, "AGENTS.md", "# Entry\n\n[Docs](docs/README.md)\n")
            write_file(root, "docs/README.md", "# Docs\n")
            write_file(root, "docs/guide/topic.md", topic("DOC-001", "Topic"))
            actions = repair_docs.plan_repairs(root)
            repair_docs.apply_repairs(root, actions)
            nested_index = root / "docs/guide/README.md"
            self.assertIn("[Topic](topic.md)", nested_index.read_text(encoding="utf-8"))
            self.assertEqual([item.code for item in audit_docs.audit(root)], [])

    def test_repair_refuses_a_concurrent_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, "docs/guide/new.md", topic("DOC-002", "New topic"))
            actions = repair_docs.plan_repairs(root)
            index = root / "docs/guide/README.md"
            index.write_text(index.read_text(encoding="utf-8") + "\nChanged\n", encoding="utf-8")
            with self.assertRaises(repair_docs.RepairConflict):
                repair_docs.apply_repairs(root, actions)
