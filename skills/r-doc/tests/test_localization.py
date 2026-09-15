from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


class PublicDocumentationLocalizationTests(unittest.TestCase):
    def test_english_and_chinese_readmes_route_to_matching_reference_languages(self) -> None:
        english = (ROOT / "README.md").read_text(encoding="utf-8")
        chinese = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

        english_targets = [target for target in LINK_PATTERN.findall(english) if target.startswith("skills/r-doc/references/")]
        chinese_targets = [target for target in LINK_PATTERN.findall(chinese) if target.startswith("skills/r-doc/references/")]

        self.assertTrue(english_targets)
        self.assertTrue(chinese_targets)
        self.assertTrue(all(not target.endswith(".zh-CN.md") for target in english_targets))
        self.assertTrue(all(target.endswith(".zh-CN.md") for target in chinese_targets))
        self.assertTrue(all((ROOT / target).is_file() for target in english_targets + chinese_targets))

    def test_localized_references_cross_link_to_their_english_canonical_files(self) -> None:
        for name in ("repair", "examples", "pitfalls"):
            chinese_path = ROOT / "skills" / "r-doc" / "references" / f"{name}.zh-CN.md"
            english_path = ROOT / "skills" / "r-doc" / "references" / f"{name}.md"
            content = chinese_path.read_text(encoding="utf-8")
            self.assertIn(f"[English version]({english_path.name})", content)


if __name__ == "__main__":
    unittest.main()
