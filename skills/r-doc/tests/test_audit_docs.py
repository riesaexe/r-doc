from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import audit_docs
from helpers import topic, valid_project, write_file


class AuditDocsTests(unittest.TestCase):
    def test_valid_project_passes_strict_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            self.assertEqual(audit_docs.audit(root), [])

    def test_repeated_read_findings_are_collapsed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            unreadable_path = root / "docs/guide/unreadable.md"
            unreadable_path.mkdir()
            findings: list[audit_docs.Finding] = []
            for _ in range(3):
                audit_docs.read_text(unreadable_path, root, findings)
            self.assertEqual([item.code for item in findings], ["read-error"])

    def test_missing_entrypoint_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_file(root, "docs/README.md", "# Docs\n")
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "missing-entrypoint" for item in findings))

    def test_broken_link_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, "docs/guide/README.md", "# Guide\n\n[Missing](missing.md)\n")
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "broken-link" for item in findings))

    def test_links_inside_code_and_comments_are_not_audited(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            content = topic("DOC-001") + "\n\n```markdown\n[Missing](missing.md)\n```\n\n`[Inline](missing-inline.md)`\n\n<!-- [Comment](missing-comment.md) -->\n"
            write_file(root, "docs/guide/doc.md", content)
            findings = audit_docs.audit(root)
            self.assertFalse(any(item.code == "broken-link" for item in findings))

    def test_existing_anchor_passes_and_missing_anchor_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            content = topic("DOC-001") + "\n\n[Guide](#guide)\n[Missing](#missing-section)\n"
            write_file(root, "docs/guide/doc.md", content)
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "broken-anchor" for item in findings))
            self.assertFalse(any(item.code == "broken-link" for item in findings))

    def test_unindexed_document_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, "docs/guide/orphan.md", topic("DOC-002", "Orphan"))
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "unindexed-document" for item in findings))

    def test_invalid_stage_is_reported_as_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, ".r-doc.yaml", "gates:\n  release: blocking\n")
            with patch.object(sys, "argv", ["audit_docs.py", "--root", str(root), "--stage", "relaese"]):
                with patch("builtins.print") as printer:
                    self.assertEqual(audit_docs.main(), 1)
            self.assertTrue(any("invalid-stage" in str(call) for call in printer.call_args_list))

    def test_superseded_document_requires_a_successor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, "docs/guide/doc.md", topic("DOC-001").replace("status: active", "status: superseded"))
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "superseded-successor-missing" for item in findings))

    def test_superseded_document_with_successor_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            old_document = topic("DOC-001").replace("status: active", "status: superseded") + "\n[Replacement](replacement.md)\n"
            write_file(root, "docs/guide/doc.md", old_document)
            replacement = topic("DOC-002", "Replacement").replace(
                "updated: 2026-09-14\n---",
                "updated: 2026-09-14\nsupersedes: DOC-001\n---",
            )
            write_file(root, "docs/guide/replacement.md", replacement)
            write_file(
                root,
                "docs/guide/README.md",
                "# Guide\n\n[Topic](doc.md)\n[Replacement](replacement.md)\n[Docs](../README.md)\n",
            )
            findings = audit_docs.audit(root)
            self.assertFalse(any(item.code == "superseded-successor-missing" for item in findings))
            self.assertFalse(any(item.code == "superseded-successor-unlinked" for item in findings))

    def test_superseded_document_must_link_to_successor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, "docs/guide/doc.md", topic("DOC-001").replace("status: active", "status: superseded"))
            replacement = topic("DOC-002", "Replacement").replace(
                "updated: 2026-09-14\n---",
                "updated: 2026-09-14\nsupersedes: DOC-001\n---",
            )
            write_file(root, "docs/guide/replacement.md", replacement)
            write_file(
                root,
                "docs/guide/README.md",
                "# Guide\n\n[Topic](doc.md)\n[Replacement](replacement.md)\n[Docs](../README.md)\n",
            )
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "superseded-successor-unlinked" for item in findings))

    def test_broken_image_is_reported_without_becoming_navigation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, "docs/guide/doc.md", topic("DOC-001") + "\n\n![Diagram](missing.png)\n")
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "broken-link" for item in findings))

    def test_unused_reference_definition_does_not_index_a_document(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, "docs/README.md", "# Docs\n\n[Entry](../AGENTS.md)\n\n[unused]: guide/README.md\n")
            findings = audit_docs.audit(root)
            codes = {item.code for item in findings}
            self.assertIn("unindexed-document", codes)
            self.assertIn("missing-navigation-link", codes)

    def test_nested_index_requires_direct_parent_link(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_file(root, "AGENTS.md", "# Entry\n\n[Docs](docs/README.md)\n")
            write_file(root, "docs/README.md", "# Docs\n\n[Entry](../AGENTS.md)\n[B](b/README.md)\n")
            write_file(root, "docs/a/README.md", "# A\n\n[Parent](../README.md)\n[Topic](topic.md)\n")
            write_file(root, "docs/a/topic.md", topic("DOC-A", "Topic A"))
            write_file(root, "docs/b/README.md", "# B\n\n[Parent](../README.md)\n[A](../a/README.md)\n")
            findings = audit_docs.audit(root)
            self.assertTrue(
                any(
                    item.code == "missing-navigation-link"
                    and item.path == "docs/README.md"
                    and "docs/a/README.md" in item.message
                    for item in findings
                )
            )

    def test_reference_style_and_parenthesized_links_are_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, "docs/guide/doc(with).md", topic("DOC-002", "With parentheses"))
            write_file(
                root,
                "docs/guide/README.md",
                "# Guide\n\n[Topic][doc]\n[Parent][parent]\n[Parenthesized](doc(with).md)\n\n[doc]: doc.md\n[parent]: ../README.md\n",
            )
            findings = audit_docs.audit(root)
            self.assertFalse(any(item.code in {"broken-link", "missing-navigation-link"} for item in findings))

    def test_resolved_link_cannot_escape_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, "docs/guide/README.md", "# Guide\n\n[Escape](../../../outside.md)\n\n[Docs](../README.md)\n")
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "link-outside-root" for item in findings))

if __name__ == "__main__":
    unittest.main()
