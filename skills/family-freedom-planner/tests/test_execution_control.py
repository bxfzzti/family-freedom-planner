import importlib.util
import json
import unittest
from pathlib import Path
from workflow_fixtures import baseline_output, state_build, stress_scenarios

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "workflow_orchestrator.py"

spec = importlib.util.spec_from_file_location("wo", SCRIPT)
wo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wo)


def base_input(topics=None, external=False):
    return {
        "run_id":"test",
        "user_text":"test",
        "selected_topics": topics or ["GENERAL"],
        "requires_external_facts": external,
    }


class ExecutionControlTests(unittest.TestCase):
    def test_legacy_known_context_rejected(self):
        data = base_input()
        data["known_context"] = {}
        with self.assertRaises(wo.WorkflowError):
            wo.init_run(data)

    def test_invalid_family_state_rejected_at_init(self):
        data = base_input()
        data["family_state"] = {"schema_version": "0.9"}
        with self.assertRaises(wo.WorkflowError):
            wo.init_run(data)

    def test_fixed_amortizing_mortgage_does_not_require_refinance(self):
        valid, _ = wo.validate_financing({
            "nominal_principal_checked": True, "refinance_failure_tested": False,
            "refinance_required": False, "loan_structure": "FULLY_AMORTIZING_FIXED_TERM",
            "compliance_status": "REQUIRES_VERIFICATION",
            "results": {"balloon_payment": 0,
                        "refinance_not_applicable_reason": "No renewal or balloon in stated contract"}}, {})
        self.assertTrue(valid)

    def test_balloon_cannot_claim_refinance_not_applicable(self):
        valid, _ = wo.validate_financing({
            "nominal_principal_checked": True, "refinance_failure_tested": False,
            "refinance_required": False, "loan_structure": "FULLY_AMORTIZING_FIXED_TERM",
            "compliance_status": "VERIFIED",
            "results": {"balloon_payment": 100000,
                        "refinance_not_applicable_reason": "claimed not applicable"}}, {})
        self.assertFalse(valid)

    def test_refinance_not_applicable_needs_reason(self):
        valid, _ = wo.validate_financing({
            "nominal_principal_checked": True, "refinance_failure_tested": False,
            "refinance_required": False, "loan_structure": "FULLY_AMORTIZING_FIXED_TERM",
            "compliance_status": "VERIFIED", "results": {"balloon_payment": 0}}, {})
        self.assertFalse(valid)

    def test_old_workflow_run_requires_reinitialization(self):
        run = wo.init_run(base_input())
        run["workflow_version"] = "1.2.0"
        with self.assertRaises(wo.WorkflowError):
            wo.next_steps(run)

    def test_empty_scenarios_do_not_count_as_stress_test(self):
        valid, _ = wo.validate_stress({
            "scenarios": {"NORMAL": {}, "STRESS": {}, "SEVERE": {}},
            "material_failures": []}, {})
        self.assertFalse(valid)

    def test_stress_cashflow_identity_checked(self):
        scenarios = stress_scenarios()
        scenarios["SEVERE"]["annual_net_cashflow"] = 999
        valid, _ = wo.validate_stress({"scenarios": scenarios, "material_failures": []}, {})
        self.assertFalse(valid)

    def test_nonfinite_baseline_rejected(self):
        valid, _ = wo.validate_baseline({
            "derived_metrics": {
                "stable_income_annual": float("nan"), "annual_spend": 1,
                "financial_assets": 1, "total_debt": 0, "net_worth": 1,
                "runway_months": 12, "high_income_dependency": 0},
            "calculation_source": "REFERENCE_ENGINE"}, {})
        self.assertFalse(valid)

    def test_orchestrator_uses_same_router(self):
        self.assertNotIn("CAREER", wo.route_topics("我40岁，想安排父母养老"))
        self.assertNotIn("HOUSING_EXISTING", wo.route_topics("我们没有房，买首套学区房"))

    def test_unknown_topic_rejected(self):
        with self.assertRaises(wo.WorkflowError):
            wo.init_run(base_input(["TYPO"]))

    def test_intake_cannot_silently_change_selected_domains(self):
        run = wo.init_run(base_input(["GENERAL"]))
        with self.assertRaises(wo.WorkflowError):
            wo.complete_step(run, "INTAKE_ROUTE", {
                "selected_topics": ["FINANCING"], "known_facts": {}, "missing_fields": []})

    def test_empty_option_checks_cannot_claim_validated(self):
        run = self._run_to_options()
        valid, _ = wo.validate_options_validate({
            "all_options_validated": True, "critical_errors": [], "option_checks": []}, run)
        self.assertFalse(valid)

    def test_failed_check_cannot_claim_validated(self):
        run = self._run_to_options()
        valid, _ = wo.validate_options_validate({
            "all_options_validated": True, "critical_errors": [],
            "option_checks": [{"id": "A", "pass": True}, {"id": "B", "pass": False}]}, run)
        self.assertFalse(valid)

    def test_illegal_jump_blocked(self):
        run = wo.init_run(base_input())
        with self.assertRaises(wo.WorkflowError):
            wo.complete_step(run, "BASELINE_CALCULATE", {
                "derived_metrics":{}, "calculation_source":"REFERENCE_ENGINE"
            })

    def test_applicable_step_cannot_skip(self):
        run = wo.init_run(base_input(["CAREER"]))
        with self.assertRaises(wo.WorkflowError):
            wo.manual_skip(run, "CAREER_ANALYSIS", "model wanted to skip")

    def test_inapplicable_steps_auto_skipped(self):
        run = wo.init_run(base_input(["CAREER"]))
        self.assertEqual(run["steps"]["HOUSING_ANALYSIS"]["status"], "SKIPPED")
        self.assertEqual(run["steps"]["CAREER_ANALYSIS"]["status"], "PENDING")

    def test_housing_requires_target_and_spread(self):
        run = wo.init_run(base_input(["HOUSING_EXISTING"]))
        # Manually prepare prereqs via helper.
        wo.complete_step(run, "INTAKE_ROUTE", {"selected_topics":["HOUSING_EXISTING"],"known_facts":{},"missing_fields":[]})
        wo.complete_step(run, "STATE_BUILD", state_build())
        wo.complete_step(run, "INPUT_VALIDATE", {"status":"READY","missing_p0":[],"conflicts":[]})
        wo.complete_step(run, "DEADLINE_IDENTIFY", {"deadlines":[],"deadline_collision":False})
        wo.complete_step(run, "BASELINE_CALCULATE", baseline_output())
        with self.assertRaises(wo.WorkflowError):
            wo.complete_step(run, "HOUSING_ANALYSIS", {
                "mode":"x",
                "results":{"target_home_considered":False,"replacement_spread_checked":False},
                "assumptions":[]
            })

    def test_financing_requires_failure_test(self):
        run = wo.init_run(base_input(["FINANCING"]))
        wo.complete_step(run, "INTAKE_ROUTE", {"selected_topics":["FINANCING"],"known_facts":{},"missing_fields":[]})
        wo.complete_step(run, "STATE_BUILD", state_build())
        wo.complete_step(run, "INPUT_VALIDATE", {"status":"READY","missing_p0":[],"conflicts":[]})
        wo.complete_step(run, "BASELINE_CALCULATE", baseline_output())
        with self.assertRaises(wo.WorkflowError):
            wo.complete_step(run, "FINANCING_ANALYSIS", {
                "nominal_principal_checked":True,
                "refinance_failure_tested":False,
                "compliance_status":"VERIFIED",
                "results":{}
            })

    def test_stress_requires_three_scenarios(self):
        run = wo.init_run(base_input())
        wo.complete_step(run, "INTAKE_ROUTE", {"selected_topics":["GENERAL"],"known_facts":{},"missing_fields":[]})
        wo.complete_step(run, "STATE_BUILD", state_build())
        wo.complete_step(run, "INPUT_VALIDATE", {"status":"READY","missing_p0":[],"conflicts":[]})
        wo.complete_step(run, "DEADLINE_IDENTIFY", {"deadlines":[],"deadline_collision":False})
        wo.complete_step(run, "BASELINE_CALCULATE", baseline_output())
        with self.assertRaises(wo.WorkflowError):
            wo.complete_step(run, "STRESS_TEST", {
                "scenarios":{"NORMAL":{},"STRESS":{}},
                "material_failures":[]
            })

    def test_gate_blocks_unresolved_p0(self):
        run = self._run_to_options(missing_p0=["target_home_budget"])
        wo.record_integrity_result(run, "BASELINE_CALCULATE", {
            "domain":"baseline","cross_checks":[{"name":"baseline","pass":True}],
            "integrity":{"status":"PASS","confidence":"HIGH","issues":[]}
        })
        run = wo.evaluate_integrity_gate(run)
        self.assertEqual(run["integrity_gate"]["status"], "PASS")
        run = wo.evaluate_gate(run)
        self.assertEqual(run["gate"]["status"], "BLOCKED")
        self.assertTrue(run["gate"]["unresolved_p0"])

    def test_external_unverified_yields_conditional_pass(self):
        run = self._run_to_options(external=True, external_verified=False)
        wo.record_integrity_result(run, "BASELINE_CALCULATE", {
            "domain":"baseline","cross_checks":[{"name":"baseline","pass":True}],
            "integrity":{"status":"PASS","confidence":"HIGH","issues":[]}
        })
        run = wo.evaluate_integrity_gate(run)
        self.assertEqual(run["integrity_gate"]["status"], "CONDITIONAL_PASS")
        run = wo.evaluate_gate(run)
        self.assertEqual(run["gate"]["status"], "CONDITIONAL_PASS")
        with self.assertRaises(wo.WorkflowError):
            wo.finalize(run, {"final_output_mode":"NORMAL","decision_summary":"x"})
        wo.finalize(run, {
            "final_output_mode":"CONDITIONAL",
            "conditional_constraints_acknowledged":True,
            "decision_summary":"conditional"
        })
        self.assertEqual(run["steps"]["FINALIZE"]["status"], "COMPLETE")

    def test_happy_path_passes(self):
        run = self._run_to_options()
        wo.record_integrity_result(run, "BASELINE_CALCULATE", {
            "domain":"baseline","cross_checks":[{"name":"baseline","pass":True}],
            "integrity":{"status":"PASS","confidence":"HIGH","issues":[]}
        })
        run = wo.evaluate_integrity_gate(run)
        self.assertEqual(run["integrity_gate"]["status"], "PASS")
        run = wo.evaluate_gate(run)
        self.assertEqual(run["gate"]["status"], "PASS")
        wo.finalize(run, {"final_output_mode":"NORMAL","decision_summary":"ok"})
        self.assertEqual(run["steps"]["FINALIZE"]["status"], "COMPLETE")

    def _run_to_options(self, missing_p0=None, external=False, external_verified=True):
        run = wo.init_run(base_input(["GENERAL"], external))
        wo.complete_step(run, "INTAKE_ROUTE", {"selected_topics":["GENERAL"],"known_facts":{},"missing_fields":[]})
        wo.complete_step(run, "STATE_BUILD", state_build())
        wo.complete_step(run, "INPUT_VALIDATE", {
            "status":"PARTIAL" if missing_p0 else "READY",
            "missing_p0":missing_p0 or [],
            "conflicts":[]
        })
        wo.complete_step(run, "DEADLINE_IDENTIFY", {"deadlines":[],"deadline_collision":False})
        wo.complete_step(run, "BASELINE_CALCULATE", baseline_output())
        if external:
            wo.complete_step(run, "EXTERNAL_FACT_CHECK", {
                "facts":[{"x":1}],
                "verification_status":"VERIFIED" if external_verified else "UNVERIFIED",
                "conditionalized_if_unverified":False if external_verified else True
            })
        wo.complete_step(run, "STRESS_TEST", {
            "scenarios":stress_scenarios(),
            "material_failures":[]
        })
        wo.complete_step(run, "OPTIONS_BUILD", {
            "options":[
                {"id":"A","label":"A","tradeoffs":[],"failure_triggers":[]},
                {"id":"B","label":"B","tradeoffs":[],"failure_triggers":[]}
            ]
        })
        wo.complete_step(run, "OPTIONS_VALIDATE", {
            "all_options_validated":True,
            "critical_errors":[],
            "option_checks":[{"id":"A","pass":True},{"id":"B","pass":True}]
        })
        return run


if __name__ == "__main__":
    unittest.main()
