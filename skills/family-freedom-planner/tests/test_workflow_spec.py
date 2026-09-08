import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class WorkflowSpecTests(unittest.TestCase):
    def test_hash_binds_actual_content(self):
        compiled = json.loads((ROOT / "assets" / "workflow.compiled.json").read_text())
        expected = compiled.pop("spec_hash")
        actual = hashlib.sha256(json.dumps(
            compiled, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(expected, actual)

    def test_yaml_and_compiled_hash_match(self):
        compiled = json.loads((ROOT/"assets"/"workflow.compiled.json").read_text(encoding="utf-8"))
        yaml_text = (ROOT/"workflow.yaml").read_text(encoding="utf-8")
        m = re.search(r"spec_hash:\s*([0-9a-f]{64})", yaml_text)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), compiled["spec_hash"])

    def test_all_required_steps_exist(self):
        compiled = json.loads((ROOT/"assets"/"workflow.compiled.json").read_text(encoding="utf-8"))
        ids = {x["id"] for x in compiled["steps"]}
        for needed in ["INPUT_VALIDATE","BASELINE_CALCULATE","STRESS_TEST","OPTIONS_VALIDATE","RECOMMENDATION_GATE","FINALIZE"]:
            self.assertIn(needed, ids)

if __name__ == "__main__":
    unittest.main()
