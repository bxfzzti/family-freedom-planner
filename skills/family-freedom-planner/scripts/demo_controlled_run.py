#!/usr/bin/env python3
"""Run synthetic data through arithmetic, integrity and recommendation gates.

No files are written and no current policy is verified. This demonstrates the
workflow, not the suitability of a housing decision for a real household.
"""
import json
from pathlib import Path

import family_freedom_engine as engine
import integrity_engine as integrity
import workflow_orchestrator as workflow

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "examples"
OUT = EX / "execution_step_outputs"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def demo():
    state = read(EX / "sample_household.json")
    metrics = engine.baseline(state)
    topics = ["HOUSING_EXISTING", "EDUCATION", "CAREER"]
    run = workflow.init_run({
        "user_text": "虚构的住房、教育、职业综合演示，不代表用户家庭",
        "selected_topics": topics, "requires_external_facts": True})
    workflow.complete_step(run, "INTAKE_ROUTE", {
        "selected_topics": topics, "known_facts": {"example_only": True}, "missing_fields": []})
    workflow.complete_step(run, "STATE_BUILD", {
        "family_state": state, "source_tags": {"all": "MODEL_ASSUMPTION"}})
    workflow.complete_step(run, "INPUT_VALIDATE", {
        "status": "READY", "missing_p0": [], "conflicts": []})
    workflow.complete_step(run, "DEADLINE_IDENTIFY", {
        "deadlines": [{"year": 2030, "type": "MODEL_ASSUMPTION",
                       "description": "Synthetic planning horizon, not predicted job loss"}],
        "deadline_collision": False})
    workflow.complete_step(run, "BASELINE_CALCULATE", {
        "derived_metrics": metrics, "calculation_source": "REFERENCE_ENGINE"})

    housing = read(OUT / "housing_analysis.json")
    housing_case = read(EX / "sell_rent_case.json")
    waiting = engine.sell_and_rent(housing_case)
    old_price = housing_case["current_home_sale_price"]
    target_price = 5000000  # Explicit synthetic target, not current market data.
    housing["results"].update(waiting)
    housing["results"].update({
        "old_home_price": old_price, "target_home_price": target_price,
        "replacement_spread": target_price - old_price,
        "current_spread": target_price - old_price,
        "sell_rent_wait_cost": waiting["wait_net_cost"]})
    housing["assumptions"] = [
        "All prices and costs are synthetic; simple interest comparison ignores principal amortization"]
    workflow.complete_step(run, "HOUSING_ANALYSIS", housing)
    education = read(OUT / "education_analysis.json")
    workflow.complete_step(run, "EDUCATION_ANALYSIS", education)

    current_income = metrics["stable_income_annual"]
    lost_income = state["income"]["high_risk_annual"]
    new_income = 150000  # Synthetic transition-income assumption.
    transition_income = current_income - lost_income + new_income
    career = {
        "current_income_state": {"household": current_income, "high_risk": lost_income},
        "transition_scenarios": [
            {"name": "current", "income": current_income},
            {"name": "transition", "income": transition_income,
             "assumption": "150000 new income, unverified synthetic scenario"},
            {"name": "severe", "income": current_income - lost_income}],
        "career_deadline": {"year": 2030, "source_type": "MODEL_ASSUMPTION"}}
    workflow.complete_step(run, "CAREER_ANALYSIS", career)
    workflow.complete_step(run, "EXTERNAL_FACT_CHECK", {
        "facts": [{"topic": "school eligibility", "status": "UNVERIFIED"}],
        "verification_status": "UNVERIFIED", "conditionalized_if_unverified": True})
    scenarios = {}
    for name, income in (("NORMAL", current_income), ("STRESS", transition_income),
                         ("SEVERE", current_income - lost_income)):
        scenarios[name] = {
            "income_annual": income, "spending_annual": metrics["annual_spend"],
            "annual_net_cashflow": income - metrics["annual_spend"],
            "assumptions": ["Synthetic income scenario; total spending includes existing debt payments"]}
    workflow.complete_step(run, "STRESS_TEST", {
        "scenarios": scenarios, "material_failures": ["School eligibility unverified"]})
    workflow.complete_step(run, "OPTIONS_BUILD", read(OUT / "options_build.json"))
    workflow.complete_step(run, "OPTIONS_VALIDATE", read(OUT / "options_validate.json"))

    checks = {
        "BASELINE_CALCULATE": integrity.validate("baseline", metrics),
        "HOUSING_ANALYSIS": integrity.validate("housing", housing["results"]),
        "EDUCATION_ANALYSIS": integrity.validate("education", {
            key: value["annual"] for key, value in education["education_scenarios"].items()}),
        "CAREER_ANALYSIS": integrity.validate("career", {
            "current_stable_income": current_income, "reduced_main_income": lost_income,
            "new_income_sources": new_income, "resulting_stable_income": transition_income})}
    for step, result in checks.items():
        workflow.record_integrity_result(run, step, result)
    workflow.evaluate_integrity_gate(run)
    workflow.evaluate_gate(run)
    workflow.finalize(run, {
        "final_output_mode": "CONDITIONAL", "conditional_constraints_acknowledged": True,
        "decision_summary": "Synthetic workflow demo only. School eligibility and market assumptions are unverified; this is not an executable household recommendation."})
    return {
        "example_only": True, "gate": run["gate"],
        "final_status": run["steps"]["FINALIZE"]["status"],
        "baseline": metrics, "housing_waiting_calculation": waiting,
        "integrity_checks": checks, "ledger": run["ledger"]}


if __name__ == "__main__":
    print(json.dumps(demo(), ensure_ascii=False, indent=2, allow_nan=False))
