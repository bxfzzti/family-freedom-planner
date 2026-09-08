import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_family_state as validator


class FamilyStateTests(unittest.TestCase):
    def setUp(self):
        self.state = json.loads((ROOT / "examples" / "sample_household.json").read_text())

    def test_sample_is_calculation_ready(self):
        self.assertEqual(validator.validate_state(self.state, True)["status"], "PASS")

    def test_before_tax_income_is_not_ready(self):
        self.state["income"]["tax_basis"] = "BEFORE_TAX"
        self.assertEqual(validator.validate_state(self.state, True)["status"], "FAIL")

    def test_unallocated_assets_are_not_ready(self):
        self.state["assets"]["unallocated_financial_assets"] = 100
        self.assertEqual(validator.validate_state(self.state, True)["status"], "FAIL")

    def test_unknown_is_not_zero(self):
        self.state["assets"]["cash"] = None
        self.assertEqual(validator.validate_state(self.state, True)["status"], "FAIL")

    def test_unknown_non_liquid_assets_block_total_assets(self):
        self.state["assets"]["other_non_liquid"] = None
        self.assertEqual(validator.validate_state(self.state, True)["status"], "FAIL")

    def test_missing_source_tag_fails(self):
        self.state["source_tags"].pop("expenses.annual_total")
        self.assertEqual(validator.validate_state(self.state)["status"], "FAIL")

    def test_boolean_amount_fails(self):
        self.state["assets"]["cash"] = True
        self.assertEqual(validator.validate_state(self.state)["status"], "FAIL")

    def test_debt_must_be_current_balance(self):
        self.state["debts"]["items"][0]["balance_basis"] = "ORIGINAL_PRINCIPAL"
        self.assertEqual(validator.validate_state(self.state, True)["status"], "FAIL")

    def test_linked_housing_debt_must_match_debt_ledger(self):
        self.state["assets"]["real_estate"][0]["linked_debt_balance"] = 900000
        self.assertEqual(validator.validate_state(self.state, True)["status"], "FAIL")

    def test_duplicate_asset_ids_fail(self):
        self.state["assets"]["real_estate"].append(
            copy.deepcopy(self.state["assets"]["real_estate"][0]))
        self.assertEqual(validator.validate_state(self.state)["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
