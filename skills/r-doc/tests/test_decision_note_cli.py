from pathlib import Path
from contextlib import redirect_stdout
import io
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import audit_docs
import decision_notes
from helpers import valid_project, write_file


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


class DecisionNoteCliTests(unittest.TestCase):
    def _prepare(self, root: Path) -> Path:
        valid_project(root)
        write_file(root, ".agents/notes/README.md", "# Decision notes\n")
        note_path = root / ".agents/notes/implemented/architecture/adopt-notes.md"
        write_file(root, ".agents/notes/implemented/architecture/adopt-notes.md", implemented_note())
        return note_path

    def test_archive_defaults_to_a_non_mutating_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            note_path = self._prepare(root)
            self.assertEqual(
                decision_notes.main(["archive", "--root", str(root), str(note_path.relative_to(root))]),
                0,
            )
            self.assertTrue(note_path.is_file())
            self.assertFalse((root / ".agents/notes/archived/architecture/adopt-notes.md").exists())

    def test_archive_json_preview_emits_one_machine_readable_document(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            note_path = self._prepare(root)
            output = io.StringIO()
            with redirect_stdout(output):
                result = decision_notes.main(["archive", "--root", str(root), "--json", str(note_path.relative_to(root))])
            self.assertEqual(result, 0)
            payload = json.loads(output.getvalue())
            self.assertFalse(payload["changed"])

    def test_archive_apply_moves_note_and_preserves_auditable_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            note_path = self._prepare(root)
            self.assertEqual(
                decision_notes.main(["archive", "--root", str(root), "--apply", str(note_path.relative_to(root))]),
                0,
            )
            archived_path = root / ".agents/notes/archived/architecture/adopt-notes.md"
            self.assertFalse(note_path.exists())
            self.assertTrue(archived_path.is_file())
            archived_text = archived_path.read_text(encoding="utf-8")
            self.assertIn("status: archived", archived_text)
            self.assertRegex(archived_text, r"archived: \d{4}-\d{2}-\d{2}")
            self.assertEqual(audit_docs.audit(root), [])

    def test_archive_refuses_an_existing_destination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            note_path = self._prepare(root)
            write_file(root, ".agents/notes/archived/architecture/adopt-notes.md", implemented_note("DEC-999", "Existing"))
            self.assertEqual(
                decision_notes.main(["archive", "--root", str(root), "--apply", str(note_path.relative_to(root))]),
                1,
            )
            self.assertTrue(note_path.is_file())

    def test_archive_rewrites_inbound_note_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare(root)
            successor = (
                implemented_note("DEC-002", "New decision")
                .replace("status: implemented", "status: proposed")
                .replace("updated: 2026-09-19\n---", "updated: 2026-09-19\nsupersedes: DEC-001\n---")
                .replace("## Decision", "## Proposal")
                .replace("## Consequences", "## Acceptance criteria")
                + "\n## Risks\n\nThe archived rationale remains reviewable.\n\n[Old decision](../../implemented/architecture/adopt-notes.md)\n"
            )
            write_file(root, ".agents/notes/proposed/architecture/new-decision.md", successor)
            note_path = root / ".agents/notes/implemented/architecture/adopt-notes.md"
            self.assertEqual(
                decision_notes.main(["archive", "--root", str(root), "--apply", str(note_path.relative_to(root))]),
                0,
            )
            successor_text = (root / ".agents/notes/proposed/architecture/new-decision.md").read_text(encoding="utf-8")
            self.assertIn("../../archived/architecture/adopt-notes.md", successor_text)
            self.assertEqual(audit_docs.audit(root), [])


if __name__ == "__main__":
    unittest.main()
