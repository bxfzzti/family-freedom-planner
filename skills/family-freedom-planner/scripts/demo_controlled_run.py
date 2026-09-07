#!/usr/bin/env python3
"""Run the v1.1 demo through the control plane."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "workflow_orchestrator.py"
EX = ROOT / "examples"
OUT = EX / "execution_step_outputs"

spec = importlib.util.spec_from_file_location("wo", SCRIPT)
wo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wo)

run = wo.init_run(json.loads((EX/"execution_run_input.json").read_text(encoding="utf-8")))

sequence = [
    ("INTAKE_ROUTE","intake_route.json"),
    ("STATE_BUILD","state_build.json"),
    ("INPUT_VALIDATE","input_validate_ready.json"),
    ("DEADLINE_IDENTIFY","deadline_identify.json"),
    ("BASELINE_CALCULATE","baseline_calculate.json"),
    ("HOUSING_ANALYSIS","housing_analysis.json"),
    ("EDUCATION_ANALYSIS","education_analysis.json"),
    ("CAREER_ANALYSIS","career_analysis.json"),
    ("EXTERNAL_FACT_CHECK","external_fact_check.json"),
    ("STRESS_TEST","stress_test.json"),
    ("OPTIONS_BUILD","options_build.json"),
    ("OPTIONS_VALIDATE","options_validate.json"),
]
for step, filename in sequence:
    output = json.loads((OUT/filename).read_text(encoding="utf-8"))
    wo.complete_step(run, step, output)

wo.evaluate_gate(run)
final = json.loads((EX/"final_output_conditional.json").read_text(encoding="utf-8"))
wo.finalize(run, final)

print(json.dumps({
    "gate":run["gate"],
    "final_status":run["steps"]["FINALIZE"]["status"],
    "ledger":run["ledger"]
}, ensure_ascii=False, indent=2))
