import importlib.util
import unittest
from pathlib import Path
from workflow_fixtures import stress_scenarios

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"scripts"/"workflow_orchestrator.py"
spec=importlib.util.spec_from_file_location("wo2",P)
wo=importlib.util.module_from_spec(spec); spec.loader.exec_module(wo)

class IntegrityGateTests(unittest.TestCase):
    def test_finalize_rechecks_changed_output(self):
        run = self._base_ready()
        wo.record_integrity_result(run, "BASELINE_CALCULATE", self._pass_result())
        wo.evaluate_integrity_gate(run)
        wo.evaluate_gate(run)
        run["steps"]["BASELINE_CALCULATE"]["output"]["derived_metrics"]["net_worth"] = 9
        with self.assertRaises(wo.WorkflowError):
            wo.finalize(run, {"final_output_mode": "NORMAL", "decision_summary": "unsafe"})

    def _pass_result(self):
        return {"domain": "baseline", "cross_checks": [{"name": "identity", "pass": True}],
                "integrity": {"status": "PASS", "confidence": "HIGH", "issues": []}}

    def test_empty_result_rejected(self):
        with self.assertRaises(wo.WorkflowError):
            wo.record_integrity_result(self._base_ready(), "BASELINE_CALCULATE", {})

    def test_pass_requires_actual_checks(self):
        result = self._pass_result()
        result["cross_checks"] = []
        with self.assertRaises(wo.WorkflowError):
            wo.record_integrity_result(self._base_ready(), "BASELINE_CALCULATE", result)

    def test_recalculation_invalidates_previous_integrity(self):
        run = self._base_ready()
        wo.record_integrity_result(run, "BASELINE_CALCULATE", self._pass_result())
        output = run["steps"]["BASELINE_CALCULATE"]["output"]
        wo.rollback_steps(run, ["BASELINE_CALCULATE"], "new input")
        self.assertNotIn("BASELINE_CALCULATE", run["integrity_results"])
        self.assertIn("BASELINE_CALCULATE", wo.next_steps(run)["available"])
        self.assertEqual(run["steps"]["STRESS_TEST"]["status"], "STALE")
        wo.complete_step(run, "BASELINE_CALCULATE", output)
        self.assertNotIn("BASELINE_CALCULATE", run["integrity_results"])

    def test_changed_output_cannot_reuse_integrity(self):
        run = self._base_ready()
        wo.record_integrity_result(run, "BASELINE_CALCULATE", self._pass_result())
        run["steps"]["BASELINE_CALCULATE"]["output"]["derived_metrics"]["net_worth"] = 9
        wo.evaluate_integrity_gate(run)
        self.assertEqual(run["integrity_gate"]["status"], "BLOCKED")

    def test_new_failure_revokes_previous_gate(self):
        run = self._base_ready()
        wo.record_integrity_result(run, "BASELINE_CALCULATE", self._pass_result())
        wo.evaluate_integrity_gate(run)
        wo.evaluate_gate(run)
        result = self._pass_result()
        result["integrity"] = {"status": "FAIL", "confidence": "LOW", "issues": ["corrected"]}
        wo.record_integrity_result(run, "BASELINE_CALCULATE", result)
        with self.assertRaises(wo.WorkflowError):
            wo.finalize(run, {"final_output_mode": "NORMAL", "decision_summary": "unsafe"})

    def _base_ready(self):
        run=wo.init_run({"selected_topics":["GENERAL"],"user_text":"x"})
        wo.complete_step(run,"INTAKE_ROUTE",{"selected_topics":["GENERAL"],"known_facts":{},"missing_fields":[]})
        wo.complete_step(run,"STATE_BUILD",{"family_state":{},"source_tags":{}})
        wo.complete_step(run,"INPUT_VALIDATE",{"status":"READY","missing_p0":[],"conflicts":[]})
        wo.complete_step(run,"DEADLINE_IDENTIFY",{"deadlines":[],"deadline_collision":False})
        wo.complete_step(run,"BASELINE_CALCULATE",{
            "derived_metrics":{
                "stable_income_annual":100,"annual_spend":50,"financial_assets":100,
                "total_debt":0,"net_worth":100,"runway_months":24,
                "high_income_dependency":0.5
            },
            "calculation_source":"REFERENCE_ENGINE"
        })
        wo.complete_step(run,"STRESS_TEST",{
            "scenarios":stress_scenarios(),
            "material_failures":[]
        })
        wo.complete_step(run,"OPTIONS_BUILD",{
            "options":[
                {"id":"A","label":"A","tradeoffs":[],"failure_triggers":[]},
                {"id":"B","label":"B","tradeoffs":[],"failure_triggers":[]}
            ]
        })
        wo.complete_step(run,"OPTIONS_VALIDATE",{
            "all_options_validated":True,
            "critical_errors":[],
            "option_checks":[{"id":"A","pass":True},{"id":"B","pass":True}]
        })
        return run

    def test_missing_integrity_check_blocks(self):
        run=self._base_ready()
        run=wo.evaluate_integrity_gate(run)
        self.assertEqual(run["integrity_gate"]["status"],"BLOCKED")

    def test_integrity_pass_allows_recommendation(self):
        run=self._base_ready()
        wo.record_integrity_result(run,"BASELINE_CALCULATE",{
            "domain":"baseline","cross_checks":[{"name":"x","pass":True}],
            "integrity":{"status":"PASS","confidence":"HIGH","issues":[]}
        })
        run=wo.evaluate_integrity_gate(run)
        self.assertEqual(run["integrity_gate"]["status"],"PASS")
        run=wo.evaluate_gate(run)
        self.assertEqual(run["gate"]["status"],"PASS")

    def test_fail_quarantines_and_blocks(self):
        run=self._base_ready()
        wo.record_integrity_result(run,"BASELINE_CALCULATE",{
            "domain":"baseline","cross_checks":[],
            "integrity":{"status":"FAIL","confidence":"LOW","issues":["bad identity"]}
        })
        self.assertEqual(run["steps"]["BASELINE_CALCULATE"]["status"],"QUARANTINED")
        with self.assertRaises(wo.WorkflowError):
            wo.evaluate_integrity_gate(run)

    def test_rollback_marks_stale(self):
        run=self._base_ready()
        run=wo.rollback_steps(run,["BASELINE_CALCULATE","STRESS_TEST","OPTIONS_BUILD","OPTIONS_VALIDATE"],"corrected input")
        self.assertEqual(run["steps"]["BASELINE_CALCULATE"]["status"],"STALE")
        self.assertEqual(run["steps"]["STRESS_TEST"]["status"],"STALE")

if __name__=="__main__":
    unittest.main()
