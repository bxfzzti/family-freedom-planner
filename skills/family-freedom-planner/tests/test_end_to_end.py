"""Actual source-bound arithmetic, gates, and correction; no mocked PASS."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import workflow_orchestrator as workflow
import plan_engine
import demo_controlled_run
from workflow_fixtures import family_state


class EndToEndTests(unittest.TestCase):
    def test_shipped_demo_completes_conditionally(self):
        result = demo_controlled_run.demo()
        self.assertEqual(result["final_status"], "COMPLETE")
        self.assertEqual(result["gate"]["status"], "CONDITIONAL_PASS")
        self.assertTrue(result["example_only"])
        self.assertEqual(result["housing_waiting_calculation"]["wait_net_cost"], 44000)
        self.assertEqual(len(result["options"]), 3)

    def finish(self, run, state):
        outputs = plan_engine.step_outputs(state)
        for step in ("STATE_BUILD", "INPUT_VALIDATE", "DEADLINE_IDENTIFY", "BASELINE_CALCULATE",
                     "STRESS_TEST", "OPTIONS_BUILD", "OPTIONS_VALIDATE"):
            workflow.complete_step(run, step, outputs[step])
        workflow.evaluate_integrity_gate(run)
        workflow.evaluate_gate(run)
        workflow.finalize(run, {"final_output_mode": "NORMAL", "decision_summary": "Synthetic budget only"})
        return outputs["BASELINE_CALCULATE"]["derived_metrics"]

    def test_calculate_then_correct_and_recompute(self):
        state = family_state()
        run = workflow.init_run({"user_text": "Synthetic budget", "selected_topics": ["GENERAL"]})
        workflow.complete_step(run, "INTAKE_ROUTE", {
            "selected_topics": ["GENERAL"], "known_facts": {}, "missing_fields": []})
        first = self.finish(run, state)
        state["assets"]["cash"] -= 300000
        workflow.rollback_steps(run, ["STATE_BUILD"], "Corrected cash")
        self.assertFalse(run["integrity_results"])
        second = self.finish(run, state)
        self.assertEqual(first["financial_assets"] - second["financial_assets"], 300000)
        self.assertEqual(run["steps"]["FINALIZE"]["status"], "COMPLETE")
