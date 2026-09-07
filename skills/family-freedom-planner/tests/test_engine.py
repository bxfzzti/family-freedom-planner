import importlib.util
import json
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


if __name__ == "__main__":
    unittest.main()
