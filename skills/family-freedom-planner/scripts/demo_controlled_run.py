#!/usr/bin/env python3
"""Run a free, offline, source-bound synthetic planning workflow. No files saved."""
import json
from pathlib import Path
import plan_engine
import family_freedom_engine as engine
import workflow_orchestrator as workflow

ROOT = Path(__file__).resolve().parents[1]


def demo():
    state = json.loads((ROOT / "examples/sample_household.json").read_text(encoding="utf-8"))
    outputs = plan_engine.step_outputs(state)
    topics = ["HOUSING_EXISTING", "FINANCING", "CAREER"]
    run = workflow.init_run({"user_text": "Synthetic source-bound housing plan",
                             "selected_topics": topics, "requires_external_facts": True})
    workflow.complete_step(run, "INTAKE_ROUTE", {
        "selected_topics": topics, "known_facts": {"example_only": True}, "missing_fields": []})
    for step in ("STATE_BUILD", "INPUT_VALIDATE", "DEADLINE_IDENTIFY", "BASELINE_CALCULATE",
                 "HOUSING_ANALYSIS", "FINANCING_ANALYSIS", "CAREER_ANALYSIS"):
        workflow.complete_step(run, step, outputs[step])
    workflow.complete_step(run, "EXTERNAL_FACT_CHECK", {
        "facts": [], "verification_status": "UNVERIFIED", "conditionalized_if_unverified": True})
    for step in ("STRESS_TEST", "OPTIONS_BUILD", "OPTIONS_VALIDATE"):
        workflow.complete_step(run, step, outputs[step])
    workflow.evaluate_integrity_gate(run)
    workflow.evaluate_gate(run)
    workflow.finalize(run, {"final_output_mode": "CONDITIONAL",
                           "conditional_constraints_acknowledged": True,
                           "decision_summary": "Synthetic source-bound comparison; verify contracts and local facts before execution."})
    waiting = engine.sell_and_rent(json.loads(
        (ROOT / "examples/sell_rent_case.json").read_text(encoding="utf-8")))
    return {"example_only": True, "gate": run["gate"],
            "final_status": run["steps"]["FINALIZE"]["status"],
            "baseline": outputs["BASELINE_CALCULATE"]["derived_metrics"],
            "housing_waiting_calculation": waiting,
            "options": outputs["STRESS_TEST"]["option_runs"],
            "integrity_checks": run["integrity_results"], "ledger": run["ledger"]}


if __name__ == "__main__":
    print(json.dumps(demo(), ensure_ascii=False, indent=2, allow_nan=False))
