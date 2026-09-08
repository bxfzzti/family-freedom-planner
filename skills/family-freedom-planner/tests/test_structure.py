import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
OPENAI = ROOT / "agents" / "openai.yaml"


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

    def test_openai_metadata_supports_implicit_invocation(self):
        text = OPENAI.read_text(encoding="utf-8")
        self.assertIn('display_name: "家庭重大决策规划助手"', text)
        self.assertIn("$family-freedom-planner", text)
        self.assertIn("allow_implicit_invocation: true", text)
        prompt = re.search(r'^  default_prompt: "(.*)"$', text, re.M).group(1)
        self.assertLessEqual(len(prompt), 128)

    def test_first_response_gate_precedes_usage_section(self):
        text = SKILL.read_text(encoding="utf-8")
        gate = text.index("## 首次回复硬门禁")
        usage = text.index("## 什么时候使用")
        self.assertLess(gate, usage)
        for phrase in ("最多三个", "不为了首次问诊搜索外部资料", "不该买"):
            self.assertIn(phrase, text[gate:usage])

    def test_referenced_files_exist(self):
        text = SKILL.read_text(encoding="utf-8")
        paths = re.findall(r"\((references/[^)]+\.md)\)", text)
        self.assertTrue(paths)
        for rel in paths:
            self.assertTrue((ROOT / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
