from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import audit_docs
import repair_docs


def write_file(root: Path, relative_path: str, content: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def topic(identifier: str, title: str = "Guide") -> str:
    return "\n".join(
        [
            "---",
            f"id: {identifier}",
            "type: guide",
            "status: active",
            f"title: {title}",
            "created: 2026-09-14",
            "updated: 2026-09-14",
            "---",
            "",
            f"# {title}",
        ]
    )


def valid_project(root: Path) -> None:
    write_file(root, "AGENTS.md", "# Entry\n\n[Docs](docs/README.md)\n")
    write_file(root, "docs/README.md", "# Docs\n\n[Guide](guide/README.md)\n")
    write_file(root, "docs/guide/README.md", "# Guide\n\n[Topic](doc.md)\n")
    write_file(root, "docs/guide/doc.md", topic("DOC-001"))


class AuditDocsTests(unittest.TestCase):
    def test_valid_project_passes_strict_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            self.assertEqual(audit_docs.audit(root), [])

    def test_nested_frontmatter_is_parsed_without_dropping_lists(self) -> None:
        text = "\n".join(
            [
                "---",
                "id: DOC-001",
                "related_code:",
                "  - src/example.ts",
                "  - src/other.ts",
                "metadata:",
                "  version: 0.2.1",
                "---",
            ]
        )
        values, _ = audit_docs.parse_frontmatter(text)
        self.assertEqual(values["related_code"], ["src/example.ts", "src/other.ts"])
        self.assertEqual(values["metadata"]["version"], "0.2.1")

    def test_malformed_frontmatter_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, "docs/guide/doc.md", "---\ntitle: [unterminated\n---\n")
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "frontmatter-parse" for item in findings))

    def test_missing_frontmatter_delimiter_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, "docs/guide/doc.md", "---\nid: DOC-001\n")
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "frontmatter-parse" for item in findings))

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

    def test_unindexed_document_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, "docs/guide/orphan.md", topic("DOC-002", "Orphan"))
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "unindexed-document" for item in findings))

    def test_sensitive_content_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, "docs/guide/doc.md", topic("DOC-001") + "\nAKIA1234567890ABCDEF\n")
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "sensitive-content" for item in findings))

    def test_extended_sensitive_patterns_are_reported(self) -> None:
        cases = {
            "jwt": "eyJ" + "hbGciOiJIUzI1NiJ9" + ".eyJ" + "zdWIiOiIxMjM0NTY3ODkwIn0" + ".signature-value-12345",
            "openai-api-key": "sk-proj-" + "1234567890abcdefghijklmnop",
            "database-connection-string": "postgresql://user:" + "real-password@db.example.test/app",
            "generic-password": "password: " + "not-a-placeholder-secret",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            for code, value in cases.items():
                with self.subTest(code=code):
                    write_file(root, "docs/guide/doc.md", topic("DOC-001") + f"\n{value}\n")
                    findings = audit_docs.audit(root)
                    self.assertTrue(any(code in item.message for item in findings))

    def test_placeholder_password_is_not_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, "docs/guide/doc.md", topic("DOC-001") + "\npassword: <your-password>\n")
            findings = audit_docs.audit(root)
            self.assertFalse(any(item.code == "sensitive-content" for item in findings))

    def test_duplicate_id_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, "docs/guide/README.md", "# Guide\n\n[Topic](doc.md)\n\n[Second](second.md)\n")
            write_file(root, "docs/guide/second.md", topic("DOC-001", "Second"))
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "duplicate-id" for item in findings))

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


if __name__ == "__main__":
    unittest.main()
