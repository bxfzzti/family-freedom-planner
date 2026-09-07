import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "state_diff.py"

spec = importlib.util.spec_from_file_location("state_diff", SCRIPT)
state_diff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(state_diff)


class StateDiffTests(unittest.TestCase):
    def test_detect_changes(self):
        old = {"income": {"x": 10}, "housing": {"price": 100}}
        new = {"income": {"x": 12}, "housing": {"price": 90}}
        result = state_diff.summarize(old, new)
        self.assertEqual(result["change_count"], 2)

    def test_classification(self):
        self.assertEqual(state_diff.classify("income.salary"), "INCOME_CHANGE")
        self.assertEqual(state_diff.classify("housing.price"), "HOUSING_PRICE_CHANGE")

    def test_added_goal(self):
        old = {"goals": ["A"]}
        new = {"goals": ["A", "B"]}
        result = state_diff.summarize(old, new)
        self.assertEqual(result["changes"][0]["delta_type"], "NEW_GOAL_OR_GOAL_CHANGE")


if __name__ == "__main__":
    unittest.main()
