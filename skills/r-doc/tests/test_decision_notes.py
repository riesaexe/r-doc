from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import audit_docs
from helpers import valid_project, write_file


def proposed_note(identifier: str = "DEC-001", title: str = "Adopt decision notes") -> str:
    return "\n".join(
        [
            "---",
            f"id: {identifier}",
            "type: decision",
            "status: proposed",
            f"title: {title}",
            "created: 2026-09-19",
            "updated: 2026-09-19",
            "related_docs:",
            "  - DOC-001",
            "---",
            "",
            f"# {title}",
            "",
            "## Problem",
            "The project needs durable rationale for non-trivial changes.",
            "",
            "## Alternatives considered",
            "Keep rationale only in commits, or store it beside the documentation.",
            "",
            "## Proposal",
            "Store decision notes under a lifecycle and class directory.",
            "",
            "## Acceptance criteria",
            "The audit reports malformed notes deterministically.",
            "",
            "## Risks",
            "The note layer must remain optional for existing projects.",
        ]
    )


def implemented_note(identifier: str = "DEC-001", title: str = "Adopt decision notes") -> str:
    return "\n".join(
        [
            "---",
            f"id: {identifier}",
            "type: decision",
            "status: implemented",
            f"title: {title}",
            "created: 2026-09-19",
            "updated: 2026-09-19",
            "---",
            "",
            f"# {title}",
            "",
            "## Problem",
            "The project needs durable rationale for non-trivial changes.",
            "",
            "## Alternatives considered",
            "Keep rationale only in commits, or store it beside the documentation.",
            "",
            "## Decision",
            "Store decision notes under a lifecycle and class directory.",
            "",
            "## Consequences",
            "The audit retains rationale while the current docs remain focused on facts.",
        ]
    )


class DecisionNotesTests(unittest.TestCase):
    def test_valid_decision_notes_are_audited_without_docs_index_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, ".agents/notes/README.md", "# Decision notes\n")
            write_file(root, ".agents/notes/proposed/architecture/adopt-notes.md", proposed_note())
            self.assertEqual(audit_docs.audit(root), [])

    def test_existing_notes_root_requires_an_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, ".agents/notes/proposed/architecture/adopt-notes.md", proposed_note())
            codes = {item.code for item in audit_docs.audit(root)}
            self.assertIn("decision-notes-index-missing", codes)

    def test_explicit_notes_root_must_exist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, ".r-doc.yaml", "decision_notes:\n  root: .decisions\n")
            codes = {item.code for item in audit_docs.audit(root)}
            self.assertIn("decision-notes-root-missing", codes)

    def test_configured_notes_root_is_audited(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, ".r-doc.yaml", "decision_notes:\n  root: .decisions\n")
            write_file(root, ".decisions/README.md", "# Decision notes\n")
            write_file(root, ".decisions/proposed/architecture/adopt-notes.md", proposed_note())
            self.assertEqual(audit_docs.audit(root), [])

    def test_absolute_notes_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, ".r-doc.yaml", "decision_notes:\n  root: /outside\n")
            codes = {item.code for item in audit_docs.audit(root)}
            self.assertIn("config-decision-notes", codes)

    def test_note_status_must_match_its_lifecycle_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, ".agents/notes/README.md", "# Decision notes\n")
            write_file(
                root,
                ".agents/notes/implemented/architecture/adopt-notes.md",
                proposed_note().replace("status: proposed", "status: implemented"),
            )
            codes = {item.code for item in audit_docs.audit(root)}
            self.assertIn("decision-note-section-missing", codes)
            self.assertIn("decision-note-implemented-proposal-heading", codes)

    def test_note_path_and_sections_are_deterministic_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, ".agents/notes/README.md", "# Decision notes\n")
            write_file(root, ".agents/notes/misc.md", proposed_note())
            codes = {item.code for item in audit_docs.audit(root)}
            self.assertIn("decision-note-path", codes)

    def test_nested_note_indexes_are_not_decision_notes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, ".agents/notes/README.md", "# Decision notes\n")
            write_file(root, ".agents/notes/proposed/architecture/README.md", "# Architecture notes\n")
            write_file(root, ".agents/notes/proposed/architecture/adopt-notes.md", proposed_note())
            codes = {item.code for item in audit_docs.audit(root)}
            self.assertNotIn("decision-note-path", codes)

    def test_note_links_and_sensitive_content_use_existing_gates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, ".agents/notes/README.md", "# Decision notes\n")
            note = proposed_note() + "\n[Missing](missing.md)\n\nAKIA1234567890ABCDEF\n"
            write_file(root, ".agents/notes/proposed/architecture/adopt-notes.md", note)
            codes = {item.code for item in audit_docs.audit(root)}
            self.assertIn("broken-link", codes)
            self.assertIn("sensitive-content", codes)

    def test_superseded_note_requires_an_existing_link(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, ".agents/notes/README.md", "# Decision notes\n")
            write_file(root, ".agents/notes/implemented/architecture/old.md", implemented_note("DEC-001", "Old decision"))
            successor = proposed_note("DEC-002", "New decision").replace(
                "  - DOC-001\n---",
                "  - DOC-001\nsupersedes: DEC-001\n---",
            )
            write_file(root, ".agents/notes/proposed/architecture/new.md", successor + "\n[Old decision](../../implemented/architecture/old.md)\n")
            codes = {item.code for item in audit_docs.audit(root)}
            self.assertNotIn("decision-note-supersedes-unlinked", codes)

    def test_superseded_note_without_link_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, ".agents/notes/README.md", "# Decision notes\n")
            write_file(root, ".agents/notes/implemented/architecture/old.md", implemented_note("DEC-001", "Old decision"))
            successor = proposed_note("DEC-002", "New decision").replace(
                "  - DOC-001\n---",
                "  - DOC-001\nsupersedes: DEC-001\n---",
            )
            write_file(root, ".agents/notes/proposed/architecture/new.md", successor)
            codes = {item.code for item in audit_docs.audit(root)}
            self.assertIn("decision-note-supersedes-unlinked", codes)

    def test_missing_decision_note_supersession_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, ".agents/notes/README.md", "# Decision notes\n")
            successor = proposed_note("DEC-002", "New decision").replace(
                "  - DOC-001\n---",
                "  - DOC-001\nsupersedes: DEC-999\n---",
            )
            write_file(root, ".agents/notes/proposed/architecture/new.md", successor)
            codes = {item.code for item in audit_docs.audit(root)}
            self.assertIn("decision-note-supersedes-missing", codes)

    def test_supersession_cycles_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_project(root)
            write_file(root, ".agents/notes/README.md", "# Decision notes\n")
            first = proposed_note("DEC-A", "First decision").replace(
                "  - DOC-001\n---",
                "  - DOC-001\nsupersedes: DEC-B\n---",
            )
            second = proposed_note("DEC-B", "Second decision").replace(
                "  - DOC-001\n---",
                "  - DOC-001\nsupersedes: DEC-A\n---",
            )
            write_file(root, ".agents/notes/proposed/architecture/first.md", first + "\n[Second](second.md)\n")
            write_file(root, ".agents/notes/proposed/architecture/second.md", second + "\n[First](first.md)\n")
            codes = {item.code for item in audit_docs.audit(root)}
            self.assertIn("decision-note-supersedes-cycle", codes)


if __name__ == "__main__":
    unittest.main()
