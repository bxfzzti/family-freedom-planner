import importlib.util
import json
import unittest
from pathlib import Path

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
        "known_context":{}
    }


class ExecutionControlTests(unittest.TestCase):
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
        wo.complete_step(run, "STATE_BUILD", {"family_state":{},"source_tags":{}})
        wo.complete_step(run, "INPUT_VALIDATE", {"status":"READY","missing_p0":[],"conflicts":[]})
        wo.complete_step(run, "DEADLINE_IDENTIFY", {"deadlines":[],"deadline_collision":False})
        wo.complete_step(run, "BASELINE_CALCULATE", {
            "derived_metrics":{
                "stable_income_annual":1,"annual_spend":1,"financial_assets":1,
                "total_debt":0,"net_worth":1,"runway_months":12,
                "high_income_dependency":0
            },
            "calculation_source":"REFERENCE_ENGINE"
        })
        with self.assertRaises(wo.WorkflowError):
            wo.complete_step(run, "HOUSING_ANALYSIS", {
                "mode":"x",
                "results":{"target_home_considered":False,"replacement_spread_checked":False},
                "assumptions":[]
            })

    def test_financing_requires_failure_test(self):
        run = wo.init_run(base_input(["FINANCING"]))
        wo.complete_step(run, "INTAKE_ROUTE", {"selected_topics":["FINANCING"],"known_facts":{},"missing_fields":[]})
        wo.complete_step(run, "STATE_BUILD", {"family_state":{},"source_tags":{}})
        wo.complete_step(run, "INPUT_VALIDATE", {"status":"READY","missing_p0":[],"conflicts":[]})
        wo.complete_step(run, "BASELINE_CALCULATE", {
            "derived_metrics":{
                "stable_income_annual":1,"annual_spend":1,"financial_assets":1,
                "total_debt":0,"net_worth":1,"runway_months":12,
                "high_income_dependency":0
            },
            "calculation_source":"REFERENCE_ENGINE"
        })
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
        wo.complete_step(run, "STATE_BUILD", {"family_state":{},"source_tags":{}})
        wo.complete_step(run, "INPUT_VALIDATE", {"status":"READY","missing_p0":[],"conflicts":[]})
        wo.complete_step(run, "DEADLINE_IDENTIFY", {"deadlines":[],"deadline_collision":False})
        wo.complete_step(run, "BASELINE_CALCULATE", {
            "derived_metrics":{
                "stable_income_annual":1,"annual_spend":1,"financial_assets":1,
                "total_debt":0,"net_worth":1,"runway_months":12,
                "high_income_dependency":0
            },
            "calculation_source":"REFERENCE_ENGINE"
        })
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
        wo.complete_step(run, "STATE_BUILD", {"family_state":{},"source_tags":{}})
        wo.complete_step(run, "INPUT_VALIDATE", {
            "status":"PARTIAL" if missing_p0 else "READY",
            "missing_p0":missing_p0 or [],
            "conflicts":[]
        })
        wo.complete_step(run, "DEADLINE_IDENTIFY", {"deadlines":[],"deadline_collision":False})
        wo.complete_step(run, "BASELINE_CALCULATE", {
            "derived_metrics":{
                "stable_income_annual":100,"annual_spend":50,"financial_assets":100,
                "total_debt":0,"net_worth":100,"runway_months":24,
                "high_income_dependency":0.5
            },
            "calculation_source":"REFERENCE_ENGINE"
        })
        if external:
            wo.complete_step(run, "EXTERNAL_FACT_CHECK", {
                "facts":[{"x":1}],
                "verification_status":"VERIFIED" if external_verified else "UNVERIFIED",
                "conditionalized_if_unverified":False if external_verified else True
            })
        wo.complete_step(run, "STRESS_TEST", {
            "scenarios":{"NORMAL":{},"STRESS":{},"SEVERE":{}},
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
