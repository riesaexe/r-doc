from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from rdoc.config import canonical_path
from rdoc.markdown import _anchor_slug, mask_markdown_non_link_regions, target_reference
from rdoc.security import is_safe_example


class RdocModuleTests(unittest.TestCase):
    def test_anchor_slug_preserves_cjk_and_emoji(self) -> None:
        self.assertEqual(_anchor_slug("目标 🚀"), "目标-🚀")

    def test_masked_markdown_preserves_real_link_text(self) -> None:
        text = "```markdown\n[Missing](missing.md)\n```\n[Real](real.md)"
        masked = mask_markdown_non_link_regions(text)
        self.assertNotIn("[Missing]", masked)
        self.assertIn("[Real]", masked)

    def test_target_reference_preserves_fragment_and_decodes_target(self) -> None:
        root = Path("project")
        source = root / "docs" / "README.md"
        reference = target_reference(source, "<guide%20notes.md#目标>", root)
        assert reference is not None
        self.assertEqual(reference.path, source.parent / "guide notes.md")
        self.assertEqual(reference.fragment, "目标")

    def test_canonical_path_rejects_paths_outside_root(self) -> None:
        root = Path.cwd()
        self.assertIsNone(canonical_path(root, root.parent))

    def test_sensitive_allowlist_is_exact(self) -> None:
        sample = "AIza" + "SyD-" + "EXAMPLE-" + "1234567890"
        self.assertTrue(is_safe_example("google-api-key", sample, {"google-api-key": (sample,)}))
        self.assertFalse(is_safe_example("google-api-key", sample))
