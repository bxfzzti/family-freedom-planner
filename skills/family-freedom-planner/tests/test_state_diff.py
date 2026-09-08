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
    def test_partial_update_preserves_other_groups(self):
        old = {"income": {"salary": 50}, "assets": {"cash": 100, "funds": 20}}
        result = state_diff.summarize(old, {"assets": {"cash": 80}}, mode="update")
        self.assertEqual(result["change_count"], 1)
        self.assertEqual(result["changes"][0]["path"], "assets.cash")

    def test_null_means_unknown_not_deletion(self):
        result = state_diff.summarize({"assets": {"cash": 100}},
                                      {"assets": {"cash": None}}, mode="update")
        self.assertEqual(result["changes"][0]["change_type"], "CHANGED")
        self.assertIsNone(result["changes"][0]["new"])

    def test_boolean_is_not_same_numeric_value(self):
        result = state_diff.summarize({"assets": {"cash": 1}}, {"assets": {"cash": True}})
        self.assertEqual(result["change_count"], 1)

    def test_empty_object_addition_visible(self):
        result = state_diff.summarize({}, {"preferences": {}})
        self.assertEqual(result["change_count"], 1)

    def test_deadline_classification(self):
        self.assertEqual(state_diff.classify("income.high_income_deadline"), "DEADLINE_CHANGE")
        self.assertEqual(state_diff.classify("deadlines"), "DEADLINE_CHANGE")

    def test_housing_debt_not_price_change(self):
        self.assertEqual(state_diff.classify("housing.primary_home_debt"), "DEBT_CHANGE")

    def test_update_does_not_mutate_original(self):
        old = {"assets": {"cash": 100}}
        merged = state_diff.merge_update(old, {"assets": {"cash": 80}})
        self.assertEqual(old["assets"]["cash"], 100)
        self.assertEqual(merged["assets"]["cash"], 80)

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
