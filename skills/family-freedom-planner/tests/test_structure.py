import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"


class StructureTests(unittest.TestCase):
    def test_skill_exists(self):
        self.assertTrue(SKILL.exists())

    def test_frontmatter(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        header = text.split("---", 2)[1]
        name = re.search(r"^name:\s*(.+)$", header, re.M).group(1).strip()
        self.assertEqual(name, ROOT.name)
        self.assertRegex(name, r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

    def test_skill_under_500_lines(self):
        lines = SKILL.read_text(encoding="utf-8").splitlines()
        self.assertLessEqual(len(lines), 500)

    def test_referenced_files_exist(self):
        text = SKILL.read_text(encoding="utf-8")
        paths = re.findall(r"\((references/[^)]+\.md)\)", text)
        self.assertTrue(paths)
        for rel in paths:
            self.assertTrue((ROOT / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
