from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import audit_docs
from helpers import topic, valid_project, write_file


class ConfigAndSensitiveTests(unittest.TestCase):
    def test_nested_frontmatter_is_parsed_without_dropping_lists(self) -> None:
        text = "\n".join(
            [
                "---",
                "id: DOC-001",
                "related_code:",
                "  - src/example.ts",
                "  - src/other.ts",
                "metadata:",
                "  version: 0.2.2",
                "---",
            ]
        )
        values, _ = audit_docs.parse_frontmatter(text)
        self.assertEqual(values["related_code"], ["src/example.ts", "src/other.ts"])
        self.assertEqual(values["metadata"]["version"], "0.2.2")

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

    def test_sensitive_content_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, "docs/guide/doc.md", topic("DOC-001") + "\nAKIA1234567890ABCDEF\n")
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "sensitive-content" for item in findings))

    def test_root_markdown_is_checked_for_links_and_sensitive_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, "NOTES.md", "[Missing](missing.md)\nAKIA1234567890ABCDEF\n")
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "broken-link" and item.path == "NOTES.md" for item in findings))
            self.assertTrue(any(item.code == "sensitive-content" and item.path == "NOTES.md" for item in findings))

    def test_root_markdown_obeys_exclude_and_readme_is_scanned_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, "README.md", "[Missing](readme-missing.md)\n")
            write_file(root, "NOTES.md", "[Missing](notes-missing.md)\nAKIA1234567890ABCDEF\n")
            write_file(root, ".r-doc.yaml", "exclude:\n  - NOTES.md\n")
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "broken-link" and item.path == "README.md" for item in findings))
            self.assertFalse(any(item.path == "NOTES.md" for item in findings))

    def test_known_aws_example_in_fenced_code_is_not_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            sample_key = "AKIA" + "IOSFODNN7EXAMPLE"
            content = topic("DOC-001") + f"\n\n```text\nAWS_ACCESS_KEY_ID={sample_key}\n```\n"
            write_file(root, "docs/guide/doc.md", content)
            findings = audit_docs.audit(root)
            self.assertFalse(any(item.code == "sensitive-content" for item in findings))

    def test_sensitive_allowlist_supports_project_specific_examples(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            sample_key = "AIzaSyD-" + "EXAMPLE-1234567890"
            write_file(root, "docs/guide/doc.md", topic("DOC-001") + f"\n{sample_key}\n")
            self.assertTrue(any(item.code == "sensitive-content" for item in audit_docs.audit(root)))
            write_file(root, ".r-doc.yaml", f"sensitive_allowlist:\n  google-api-key:\n    - {sample_key}\n")
            findings = audit_docs.audit(root)
            self.assertFalse(any(item.code == "sensitive-content" for item in findings))

    def test_invalid_sensitive_allowlist_code_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, ".r-doc.yaml", "sensitive_allowlist:\n  unknown-detector:\n    - documented-example\n")
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "config-sensitive-allowlist" for item in findings))

    def test_related_code_missing_file_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            content = topic("DOC-001").replace(
                "updated: 2026-09-14\n---",
                "updated: 2026-09-14\nrelated_code:\n  - src/ghost.ts\n---",
            )
            write_file(root, "docs/guide/doc.md", content)
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "related-code-missing" for item in findings))

    def test_related_code_directory_is_not_accepted_as_a_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            (root / "src").mkdir()
            content = topic("DOC-001").replace(
                "updated: 2026-09-14\n---",
                "updated: 2026-09-14\nrelated_code:\n  - src\n---",
            )
            write_file(root, "docs/guide/doc.md", content)
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "related-code-missing" for item in findings))

    def test_planned_code_allows_a_future_file_without_weakening_related_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            content = topic("DOC-001").replace(
                "updated: 2026-09-14\n---",
                "updated: 2026-09-14\nplanned_code:\n  - src/future.ts\n---",
            )
            write_file(root, "docs/guide/doc.md", content)
            findings = audit_docs.audit(root)
            self.assertFalse(any(item.code == "planned-code-outside-root" for item in findings))
            self.assertFalse(any(item.code == "related-code-missing" for item in findings))

    def test_planned_code_cannot_leave_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            content = topic("DOC-001").replace(
                "updated: 2026-09-14\n---",
                "updated: 2026-09-14\nplanned_code:\n  - ../future.ts\n---",
            )
            write_file(root, "docs/guide/doc.md", content)
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "planned-code-outside-root" for item in findings))

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

    def test_chinese_placeholder_password_is_not_reported(self) -> None:
        cases = [
            "password: 你的数据库密码",
            "passwd: 请输入你的密码",
            "pwd: 示例口令",
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            for value in cases:
                with self.subTest(value=value):
                    write_file(root, "docs/guide/doc.md", topic("DOC-001") + f"\n{value}\n")
                    findings = audit_docs.audit(root)
                    self.assertFalse(any("generic-password" in item.message for item in findings))

            write_file(root, "docs/guide/doc.md", topic("DOC-001") + "\npassword: 这是一个真实的生产口令\n")
            findings = audit_docs.audit(root)
            self.assertTrue(any("generic-password" in item.message for item in findings))

    def test_configured_docs_root_and_excluded_directory_are_applied(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_file(root, "AGENTS.md", "# Entry\n\n[Docs](documentation/README.md)\n")
            write_file(root, "documentation/README.md", "# Documentation\n\n[Guide](guide.md)\n\n[Entry](../AGENTS.md)\n")
            write_file(root, "documentation/guide.md", topic("DOC-001", "Guide"))
            write_file(root, "documentation/generated/orphan.md", topic("DOC-002", "Generated"))
            write_file(
                root,
                ".r-doc.yaml",
                "docs_root: documentation\nexclude:\n  - generated\nrequired_document_types:\n  - guide\ngates:\n  review: audit\n",
            )
            findings = audit_docs.audit(root)
            self.assertEqual(findings, [])
            config, problems = audit_docs.load_project_config(root)
            self.assertEqual(problems, [])
            self.assertEqual(config.docs_root, "documentation")
            self.assertEqual(config.gate_for("review"), "audit")

    def test_invalid_or_duplicate_config_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, ".r-doc.yaml", "docs_root: ../outside\nunknown: true\n")
            write_file(root, "r-doc.yaml", "docs_root: docs\n")
            findings = audit_docs.audit(root)
            codes = {item.code for item in findings}
            self.assertIn("config-duplicate", codes)
            self.assertIn("config-unknown", codes)
            self.assertIn("config-docs-root", codes)

    def test_metadata_relationships_and_title_consistency_are_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            content = topic("DOC-001").replace("title: Guide\n", "title: Wrong title\nrelated_docs:\n  - MISSING\n")
            write_file(root, "docs/guide/doc.md", content.replace("# Guide", "# Actual title"))
            findings = audit_docs.audit(root)
            codes = {item.code for item in findings}
            self.assertIn("metadata-title", codes)
            self.assertIn("related-doc-missing", codes)

    def test_relationship_requirements_are_enforced_by_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, ".r-doc.yaml", "relationships:\n  require_for:\n    guide:\n      - design\n")
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "relationship-required" for item in findings))

    def test_stage_gate_promotes_warnings_to_failures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, ".r-doc.yaml", "gates:\n  review: audit\n")
            write_file(root, "docs/guide/no-meta.md", "# No metadata\n")
            write_file(root, "docs/guide/README.md", "# Guide\n\n[Topic](doc.md)\n[No metadata](no-meta.md)\n[Docs](../README.md)\n")
            with patch.object(sys, "argv", ["audit_docs.py", "--root", str(root), "--stage", "review"]):
                with patch("builtins.print"):
                    self.assertEqual(audit_docs.main(), 1)
            with patch.object(sys, "argv", ["audit_docs.py", "--root", str(root)]):
                with patch("builtins.print"):
                    self.assertEqual(audit_docs.main(), 0)

    def test_updated_date_cannot_precede_created_date(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, "docs/guide/doc.md", topic("DOC-001").replace("created: 2026-09-14", "created: 2026-09-15"))
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "metadata-date-order" for item in findings))

    def test_duplicate_id_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, "docs/guide/README.md", "# Guide\n\n[Topic](doc.md)\n\n[Second](second.md)\n")
            write_file(root, "docs/guide/second.md", topic("DOC-001", "Second"))
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "duplicate-id" for item in findings))
