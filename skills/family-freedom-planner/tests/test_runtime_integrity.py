import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts" / "workflow_orchestrator.py"
SPEC = importlib.util.spec_from_file_location("runtime_integrity_workflow", PATH)
wo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wo)


def run_with(step, output):
    steps = {"OPTIONS_BUILD": {"output": {"options": []}},
             "STRESS_TEST": {"output": {}}}
    steps[step] = {"output": output}
    return {"steps": steps}


class RuntimeIntegrityTests(unittest.TestCase):
    def test_malformed_output_becomes_fail_not_exception(self):
        run = run_with("HOUSING_ANALYSIS", {"results": {"options": [None]}})
        result = wo.safe_runtime_integrity_for_step(run, "HOUSING_ANALYSIS")
        self.assertEqual(result["integrity"]["status"], "FAIL")
        self.assertIn("runtime verification error", result["integrity"]["issues"][0])

    def housing(self):
        return {"results": {"options": [
            {"option_id": "A", "pre_purchase_liquid_assets": 400,
             "cash_outlay": 240, "sale_net_inflow": 0,
             "post_purchase_liquid_assets": 160,
             "old_home_price": 350, "target_home_price": 500,
             "replacement_spread": 150},
            {"option_id": "B", "pre_purchase_liquid_assets": 400,
             "cash_outlay": 200, "sale_net_inflow": 0,
             "post_purchase_liquid_assets": 200,
             "old_home_price": 350, "target_home_price": 450,
             "replacement_spread": 100}]}}

    def test_every_housing_option_recomputed(self):
        run = run_with("HOUSING_ANALYSIS", self.housing())
        self.assertEqual(wo.runtime_integrity_for_step(run, "HOUSING_ANALYSIS")
                         ["integrity"]["status"], "PASS")
        run["steps"]["HOUSING_ANALYSIS"]["output"]["results"]["options"][1][
            "post_purchase_liquid_assets"] = 999
        self.assertEqual(wo.runtime_integrity_for_step(run, "HOUSING_ANALYSIS")
                         ["integrity"]["status"], "FAIL")

    def test_every_mortgage_recomputed(self):
        loans = [{"option_id": "A", "loan_structure": "FULLY_AMORTIZING_FIXED_TERM",
                  "refinance_required": False, "principal": 120000,
                  "annual_rate": 0, "years": 10, "monthly_payment": 1000,
                  "balloon_payment": 0},
                 {"option_id": "B", "loan_structure": "FULLY_AMORTIZING_FIXED_TERM",
                  "refinance_required": False, "principal": 240000,
                  "annual_rate": 0, "years": 10, "monthly_payment": 2000,
                  "balloon_payment": 0}]
        run = run_with("FINANCING_ANALYSIS", {"results": {"loans": loans}})
        self.assertEqual(wo.runtime_integrity_for_step(run, "FINANCING_ANALYSIS")
                         ["integrity"]["status"], "PASS")
        loans[1]["monthly_payment"] = 1
        self.assertEqual(wo.runtime_integrity_for_step(run, "FINANCING_ANALYSIS")
                         ["integrity"]["status"], "FAIL")

    def test_education_and_career_recomputed(self):
        education = run_with("EDUCATION_ANALYSIS", {
            "education_scenarios": {"BASE": {"annual": 1}, "MID": {"annual": 3},
                                    "HIGH": {"annual": 2}}})
        self.assertEqual(wo.runtime_integrity_for_step(education, "EDUCATION_ANALYSIS")
                         ["integrity"]["status"], "FAIL")
        career = run_with("CAREER_ANALYSIS", {"integrity_inputs": {
            "current_stable_income": 60, "reduced_main_income": 40,
            "new_income_sources": 10, "resulting_stable_income": 30}})
        self.assertEqual(wo.runtime_integrity_for_step(career, "CAREER_ANALYSIS")
                         ["integrity"]["status"], "PASS")
        career["steps"]["CAREER_ANALYSIS"]["output"]["integrity_inputs"][
            "resulting_stable_income"] = 40
        self.assertEqual(wo.runtime_integrity_for_step(career, "CAREER_ANALYSIS")
                         ["integrity"]["status"], "FAIL")

    def test_stress_option_result_must_match_recalculation(self):
        input_data = {
            "initial_low_risk_assets": 100, "upfront_net_inflow": 0,
            "upfront_outflow": 0, "protected_reserve": 20, "horizon_months": 12,
            "scenarios": {name: {"income_annual": 12, "spending_annual": 12,
                                  "changes": [], "one_off_expenses": []}
                          for name in ("NORMAL", "STRESS", "SEVERE")}}
        annual = {name: {"income_annual": 12, "spending_annual": 12,
                         "annual_net_cashflow": 0, "assumptions": []}
                  for name in ("NORMAL", "STRESS", "SEVERE")}
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import decision_cashflow
        result = decision_cashflow.simulate(input_data)
        run = run_with("STRESS_TEST", {"scenarios": annual, "material_failures": [],
                                       "option_runs": [{"option_id": "A",
                                                        "input": input_data,
                                                        "result": result}]})
        self.assertEqual(wo.runtime_integrity_for_step(run, "STRESS_TEST")
                         ["integrity"]["status"], "PASS")
        run["steps"]["STRESS_TEST"]["output"]["option_runs"][0]["result"][
            "scenarios"]["SEVERE"]["ending_low_risk_assets"] = 999
        self.assertEqual(wo.runtime_integrity_for_step(run, "STRESS_TEST")
                         ["integrity"]["status"], "FAIL")

    def test_option_ids_must_cover_stress_runs(self):
        run = {"steps": {
            "OPTIONS_BUILD": {"output": {"options": [{"id": "A"}, {"id": "B"}]}},
            "OPTIONS_VALIDATE": {"output": {"all_options_validated": True,
                "critical_errors": [], "option_checks": [
                    {"id": "A", "pass": True}, {"id": "B", "pass": True}]}},
            "STRESS_TEST": {"output": {"option_runs": [{"option_id": "A"}]}}}}
        self.assertEqual(wo.runtime_integrity_for_step(run, "OPTIONS_VALIDATE")
                         ["integrity"]["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
