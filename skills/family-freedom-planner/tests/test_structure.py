import re
import json
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

    def test_all_json_assets_and_examples_parse(self):
        for directory in (ROOT / "assets", ROOT / "examples"):
            for path in directory.rglob("*.json"):
                with self.subTest(path=path):
                    json.loads(path.read_text(encoding="utf-8"))

    def test_schema_references_exist(self):
        for path in (ROOT / "assets").glob("*.schema.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            for ref in re.findall(r'"\$ref"\s*:\s*"([^"]+)"', path.read_text()):
                if "://" not in ref and not ref.startswith("#"):
                    self.assertTrue((path.parent / ref).exists(), f"{path}: {ref}")


if __name__ == "__main__":
    unittest.main()
