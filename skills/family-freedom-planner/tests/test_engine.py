import importlib.util
import json
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "scripts" / "family_freedom_engine.py"

spec = importlib.util.spec_from_file_location("engine", ENGINE)
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)


class EngineTests(unittest.TestCase):
    def test_zero_rate_mortgage(self):
        self.assertAlmostEqual(engine.mortgage_payment(120000, 0, 10), 1000)

    def test_baseline_identity(self):
        state = json.loads((ROOT / "examples" / "sample_household.json").read_text(encoding="utf-8"))
        result = engine.baseline(state)
        self.assertAlmostEqual(result["net_worth"], result["total_assets"] - result["total_debt"])

    def test_more_rent_increases_wait_cost(self):
        case = json.loads((ROOT / "examples" / "sell_rent_case.json").read_text(encoding="utf-8"))
        a = engine.sell_and_rent(case)
        case["monthly_rent"] += 1000
        b = engine.sell_and_rent(case)
        self.assertGreater(b["wait_net_cost"], a["wait_net_cost"])

    def test_higher_safe_return_reduces_wait_cost(self):
        case = json.loads((ROOT / "examples" / "sell_rent_case.json").read_text(encoding="utf-8"))
        a = engine.sell_and_rent(case)
        case["low_risk_return"] += 0.01
        b = engine.sell_and_rent(case)
        self.assertLess(b["wait_net_cost"], a["wait_net_cost"])

    def test_less_refinance_increases_gap(self):
        case = json.loads((ROOT / "examples" / "refinance_case.json").read_text(encoding="utf-8"))
        a = engine.refinance(case)
        case["confirmed_refinance_amount"] -= 500000
        b = engine.refinance(case)
        self.assertGreaterEqual(b["refinance_gap"], a["refinance_gap"])

    def test_empty_baseline_does_not_become_zero_household(self):
        with self.assertRaises(ValueError):
            engine.baseline({})

    def test_capsule_is_not_engine_input(self):
        capsule = json.loads((ROOT / "examples" / "family-context-old.json").read_text())
        with self.assertRaises(ValueError):
            engine.baseline(capsule)

    def test_nonfinite_and_boolean_amounts_rejected(self):
        for value in (math.nan, math.inf, -math.inf, True, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                engine.mortgage_payment(value, 0.03, 30)

    def test_submonth_term_rejected(self):
        with self.assertRaises(ValueError):
            engine.mortgage_payment(1000, 0, 0.001)

    def test_tiny_rate_is_numerically_stable(self):
        payment = engine.mortgage_payment(120000, 1e-16, 10)
        self.assertAlmostEqual(payment, 1000, places=7)

    def test_unknown_debt_rejected(self):
        state = json.loads((ROOT / "examples" / "sample_household.json").read_text())
        state["debts"]["items"][0]["balance"] = None
        with self.assertRaises(ValueError):
            engine.baseline(state)

    def test_negative_cash_rejected(self):
        state = json.loads((ROOT / "examples" / "sample_household.json").read_text())
        state["assets"]["cash"] = -1
        with self.assertRaises(ValueError):
            engine.baseline(state)

    def test_mandatory_cannot_exceed_total_spend(self):
        state = json.loads((ROOT / "examples" / "sample_household.json").read_text())
        state["expenses"]["annual_mandatory"] = 999999
        with self.assertRaises(ValueError):
            engine.baseline(state)

    def test_unknown_risk_income_is_not_zero_dependency(self):
        state = json.loads((ROOT / "examples" / "sample_household.json").read_text())
        state["income"].pop("high_risk_annual")
        self.assertIsNone(engine.baseline(state)["high_income_dependency"])

    def test_before_tax_state_cannot_be_calculated(self):
        state = json.loads((ROOT / "examples" / "sample_household.json").read_text())
        state["income"]["tax_basis"] = "BEFORE_TAX"
        with self.assertRaises(ValueError):
            engine.baseline(state)

    def test_missing_refinance_is_not_safe(self):
        with self.assertRaises(ValueError):
            engine.refinance({})


if __name__ == "__main__":
    unittest.main()
