from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

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
    write_file(root, "docs/README.md", "# Docs\n\n[Guide](guide/README.md)\n\n[Entry](../AGENTS.md)\n")
    write_file(root, "docs/guide/README.md", "# Guide\n\n[Topic](doc.md)\n\n[Docs](../README.md)\n")
    write_file(root, "docs/guide/doc.md", topic("DOC-001"))


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

    def test_root_markdown_is_checked_for_links_and_sensitive_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, "NOTES.md", "[Missing](missing.md)\nAKIA1234567890ABCDEF\n")
            findings = audit_docs.audit(root)
            self.assertTrue(any(item.code == "broken-link" and item.path == "NOTES.md" for item in findings))
            self.assertTrue(any(item.code == "sensitive-content" and item.path == "NOTES.md" for item in findings))

    def test_known_aws_example_in_fenced_code_is_not_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            sample_key = "AKIA" + "IOSFODNN7EXAMPLE"
            content = topic("DOC-001") + f"\n\n```text\nAWS_ACCESS_KEY_ID={sample_key}\n```\n"
            write_file(root, "docs/guide/doc.md", content)
            findings = audit_docs.audit(root)
            self.assertFalse(any(item.code == "sensitive-content" for item in findings))

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
