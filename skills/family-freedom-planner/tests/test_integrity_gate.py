import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"scripts"/"workflow_orchestrator.py"
spec=importlib.util.spec_from_file_location("wo2",P)
wo=importlib.util.module_from_spec(spec); spec.loader.exec_module(wo)

class IntegrityGateTests(unittest.TestCase):
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
            "scenarios":{"NORMAL":{},"STRESS":{},"SEVERE":{}},
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
