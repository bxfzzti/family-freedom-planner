"""Run real arithmetic through the actual workflow, including correction."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import family_freedom_engine as calculator
import integrity_engine
import workflow_orchestrator as workflow
import demo_controlled_run


class EndToEndTests(unittest.TestCase):
    def test_shipped_demo_completes_conditionally(self):
        result = demo_controlled_run.demo()
        self.assertEqual(result["final_status"], "COMPLETE")
        self.assertEqual(result["gate"]["status"], "CONDITIONAL_PASS")
        self.assertTrue(result["example_only"])
        self.assertEqual(result["housing_waiting_calculation"]["wait_net_cost"], 44000)

    def setUp(self):
        self.state = json.loads((ROOT / "examples" / "sample_household.json").read_text())

    def finish_from_state(self, run, state, financing=None):
        workflow.complete_step(run, "STATE_BUILD", {
            "family_state": state, "source_tags": state["source_tags"]})
        workflow.complete_step(run, "INPUT_VALIDATE", {
            "status": "READY", "missing_p0": [], "conflicts": []})
        workflow.complete_step(run, "DEADLINE_IDENTIFY", {
            "deadlines": [], "deadline_collision": False})
        metrics = calculator.baseline(state)
        workflow.complete_step(run, "BASELINE_CALCULATE", {
            "derived_metrics": metrics, "calculation_source": "REFERENCE_ENGINE"})
        if financing is not None:
            workflow.complete_step(run, "FINANCING_ANALYSIS", financing)
        scenarios = {}
        for name, multiplier in (("NORMAL", 1), ("STRESS", 0.5), ("SEVERE", 0)):
            income = metrics["stable_income_annual"] * multiplier
            spend = metrics["annual_spend"]
            scenarios[name] = {
                "income_annual": income, "spending_annual": spend,
                "annual_net_cashflow": income - spend,
                "assumptions": [f"Synthetic income multiplier {multiplier}"]}
        workflow.complete_step(run, "STRESS_TEST", {
            "scenarios": scenarios, "material_failures": ["Severe scenario has a cash deficit"]})
        workflow.complete_step(run, "OPTIONS_BUILD", {"options": [
            {"id": "current", "label": "保持支出", "tradeoffs": ["预算缓冲较少"],
             "failure_triggers": ["收入下降后需复盘"]},
            {"id": "lower", "label": "减少可选支出", "tradeoffs": ["可选消费减少"],
             "failure_triggers": ["无法实际降低支出"]}]})
        workflow.complete_step(run, "OPTIONS_VALIDATE", {
            "all_options_validated": True, "critical_errors": [],
            "option_checks": [{"id": "current", "pass": True}, {"id": "lower", "pass": True}]})
        evidence = integrity_engine.validate("baseline", metrics)
        self.assertEqual(evidence["integrity"]["status"], "PASS")
        workflow.record_integrity_result(run, "BASELINE_CALCULATE", evidence)
        if financing is not None:
            finance_evidence = integrity_engine.validate("financing", financing["results"])
            self.assertEqual(finance_evidence["integrity"]["status"], "PASS")
            workflow.record_integrity_result(run, "FINANCING_ANALYSIS", finance_evidence)
        workflow.evaluate_integrity_gate(run)
        workflow.evaluate_gate(run)
        conditional = run["gate"]["status"] == "CONDITIONAL_PASS"
        workflow.finalize(run, {
            "final_output_mode": "CONDITIONAL" if conditional else "NORMAL",
            "conditional_constraints_acknowledged": conditional,
            "decision_summary": "Synthetic budget comparison only; not a real recommendation"})
        return metrics

    def test_ordinary_mortgage_runs_but_unverified_contract_stays_conditional(self):
        run = workflow.init_run({
            "user_text": "Synthetic ordinary mortgage; no external flag",
            "selected_topics": ["FINANCING"], "requires_external_facts": False})
        workflow.complete_step(run, "INTAKE_ROUTE", {
            "selected_topics": ["FINANCING"], "known_facts": {}, "missing_fields": []})
        financing = {
            "nominal_principal_checked": True, "refinance_failure_tested": False,
            "refinance_required": False, "loan_structure": "FULLY_AMORTIZING_FIXED_TERM",
            "compliance_status": "REQUIRES_VERIFICATION",
            "results": {
                "loan_structure": "FULLY_AMORTIZING_FIXED_TERM", "refinance_required": False,
                "principal": 120000, "annual_rate": 0, "years": 10,
                "monthly_payment": calculator.mortgage_payment(120000, 0, 10),
                "balloon_payment": 0, "refinance_not_applicable_reason": "Synthetic amortizing loan"}}
        self.finish_from_state(run, self.state, financing)
        self.assertEqual(run["steps"]["FINALIZE"]["status"], "COMPLETE")
        self.assertEqual(run["gate"]["status"], "CONDITIONAL_PASS")
        self.assertIn("financing contract/compliance must be verified before execution",
                      run["gate"]["conditional_constraints"])

    def test_calculate_validate_finalize_then_correct_and_recompute(self):
        run = workflow.init_run({
            "user_text": "虚构家庭预算对比，仅作代码验收", "selected_topics": ["GENERAL"]})
        workflow.complete_step(run, "INTAKE_ROUTE", {
            "selected_topics": ["GENERAL"], "known_facts": {}, "missing_fields": []})
        first = self.finish_from_state(run, self.state)
        self.assertEqual(run["steps"]["FINALIZE"]["status"], "COMPLETE")
        corrected = copy.deepcopy(self.state)
        corrected["assets"]["cash"] -= 300000
        workflow.rollback_steps(run, ["STATE_BUILD"], "corrected synthetic cash")
        self.assertIsNone(run["gate"])
        self.assertFalse(run["integrity_results"])
        self.assertIn("STATE_BUILD", workflow.next_steps(run)["available"])
        second = self.finish_from_state(run, corrected)
        self.assertEqual(first["financial_assets"] - second["financial_assets"], 300000)
        self.assertLess(second["runway_months"], first["runway_months"])
        self.assertEqual(run["steps"]["FINALIZE"]["status"], "COMPLETE")


if __name__ == "__main__":
    unittest.main()
