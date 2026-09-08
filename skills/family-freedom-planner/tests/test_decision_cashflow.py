import copy
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import decision_cashflow as engine


class CashflowTests(unittest.TestCase):
    def setUp(self):
        scenario = {"income_annual": 0, "spending_annual": 24000,
                    "changes": [], "one_off_expenses": []}
        self.case = {"initial_low_risk_assets": 120000, "upfront_net_inflow": 0,
                     "upfront_outflow": 0, "protected_reserve": 20000,
                     "horizon_months": 72, "scenarios": {
                         key: copy.deepcopy(scenario)
                         for key in ("NORMAL", "STRESS", "SEVERE")}}

    def result(self):
        return engine.simulate(self.case)["scenarios"]["STRESS"]

    def test_reserve_not_subtracted_twice(self):
        result = self.result()
        self.assertEqual(result["first_reserve_breach_month"], 51)
        self.assertEqual(result["first_cash_shortfall_month"], 61)
        self.assertEqual(result["ending_low_risk_assets"], -24000)

    def test_positive_cashflow_is_horizon_limited(self):
        self.case["scenarios"]["STRESS"]["income_annual"] = 36000
        result = self.result()
        self.assertIsNone(result["first_reserve_breach_month"])
        self.assertEqual(result["ending_low_risk_assets"], 192000)

    def test_income_drop_starts_in_declared_month(self):
        scenario = self.case["scenarios"]["STRESS"]
        scenario["income_annual"] = 24000
        scenario["changes"] = [{"month": 13, "income_annual": 0}]
        self.assertEqual(self.result()["first_reserve_breach_month"], 63)

    def test_one_off_cost_causes_early_breach(self):
        self.case["scenarios"]["STRESS"]["one_off_expenses"] = [
            {"month": 1, "amount": 100000}]
        self.assertEqual(self.result()["first_reserve_breach_month"], 1)

    def test_upfront_cash_gap_is_month_zero(self):
        self.case["upfront_outflow"] = 130000
        self.assertEqual(self.result()["first_cash_shortfall_month"], 0)

    def test_unknown_income_not_assumed_zero(self):
        self.case["scenarios"]["STRESS"]["income_annual"] = None
        with self.assertRaises(ValueError):
            self.result()

    def test_missing_severe_scenario_rejected(self):
        del self.case["scenarios"]["SEVERE"]
        with self.assertRaises(ValueError):
            self.result()

    def test_out_of_horizon_event_rejected(self):
        self.case["scenarios"]["STRESS"]["one_off_expenses"] = [
            {"month": 73, "amount": 100}]
        with self.assertRaises(ValueError):
            self.result()

    def test_duplicate_change_month_rejected(self):
        self.case["scenarios"]["STRESS"]["changes"] = [
            {"month": 1, "income_annual": 0}, {"month": 1, "spending_annual": 1}]
        with self.assertRaises(ValueError):
            self.result()

    def test_higher_spend_cannot_improve_buffer(self):
        before = self.result()
        self.case["scenarios"]["STRESS"]["spending_annual"] *= 2
        after = self.result()
        self.assertLess(after["first_reserve_breach_month"], before["first_reserve_breach_month"])
        self.assertGreater(after["maximum_cash_shortfall"], before["maximum_cash_shortfall"])


if __name__ == "__main__":
    unittest.main()
