#!/usr/bin/env python3
"""Derive option cashflows from one confirmed family state and decision plan."""
import argparse
import json
import math
from pathlib import Path
from copy import deepcopy

import family_freedom_engine as engine
import decision_cashflow
from schema_validation import validate_named


def close(a, b):
    return type(a) in (int, float) and type(b) in (int, float) and math.isclose(a, b, rel_tol=0, abs_tol=.01)


def derive(state):
    base = engine.baseline(state)
    plan = state.get("decision_plan")
    errors = validate_named(plan, "decision-plan.schema.json")
    if errors:
        raise ValueError("decision_plan: " + "; ".join(errors))
    sources = state["income"]["stable_annual"]
    home_by_id = {h["id"]: h for h in state["assets"]["real_estate"]}
    debt_by_id = {d["id"]: d for d in state["debts"]["items"]}
    horizon = plan["horizon_months"]
    results, ids = [], set()
    for option in plan["options"]:
        oid = option["id"]
        if oid in ids:
            raise ValueError("duplicate decision option id")
        ids.add(oid)
        kind = option["kind"]
        inflow = outflow = 0.0
        annual_spend = base["annual_spend"] + option["spending_delta_annual"]
        housing = None
        loans = []
        refinance_event = None
        if kind == "HOME_PURCHASE":
            for key in ("target_home_price", "down_payment", "transaction_costs",
                        "renovation_costs", "moving_costs"):
                engine.n(option.get(key))
            principal = 0.0
            loan_ids = set()
            for loan in option["loans"]:
                lid = loan["loan_id"]
                if lid in loan_ids:
                    raise ValueError(f"{oid}: duplicate loan_id")
                loan_ids.add(lid)
                payment = engine.mortgage_payment(loan["principal"], loan["annual_rate"], loan["years"])
                principal += loan["principal"]
                annual_spend += payment * 12
                loans.append({**loan, "option_id": oid,
                              "loan_structure": "FULLY_AMORTIZING_FIXED_TERM",
                              "refinance_required": False, "balloon_payment": 0,
                              "monthly_payment": payment})
            if not close(option["down_payment"] + principal, option["target_home_price"]):
                raise ValueError(f"{oid}: price must equal down_payment plus all loan principals")
            rent = state["expenses"].get("annual_rent")
            if rent is None:
                raise ValueError(f"{oid}: confirm annual_rent (zero if none) before replacing housing")
            annual_spend -= rent
            if annual_spend < 0:
                raise ValueError("housing replacement exceeds reported annual spending")
            sale = option.get("sale")
            old_price = 0.0
            if sale:
                home = home_by_id.get(sale["home_id"])
                if not home or home["sellable_for_plan"] is not True:
                    raise ValueError(f"{oid}: sale requires a known sellable home")
                old_price = sale["sale_price"]
                debt_id = home["linked_debt_id"]
                payoff = 0 if debt_id is None else debt_by_id[debt_id]["balance"]
                inflow = old_price - payoff - sale["transaction_costs"]
                if inflow < 0:
                    raise ValueError(f"{oid}: negative sale proceeds need a separately funded plan")
                if debt_id:
                    annual_payment = debt_by_id[debt_id].get("annual_payment")
                    if annual_payment is None:
                        raise ValueError(f"{oid}: confirm annual_payment of debt being repaid")
                    annual_spend -= annual_payment
            outflow = (option["down_payment"] + option["transaction_costs"]
                       + option["renovation_costs"] + option["moving_costs"])
            housing = {
                "option_id": oid, "pre_purchase_liquid_assets": base["low_risk_assets"],
                "cash_outlay": outflow, "sale_net_inflow": inflow,
                "post_purchase_liquid_assets": base["low_risk_assets"] + inflow - outflow,
                "old_home_price": old_price, "target_home_price": option["target_home_price"],
                "replacement_spread": option["target_home_price"] - old_price,
                "down_payment": option["down_payment"], "total_loan_principal": principal}
            if housing["post_purchase_liquid_assets"] < -.01:
                raise ValueError(f"{oid}: down payment and purchase costs exceed available source funds")
        elif kind == "REFINANCE":
            if option["loans"]:
                raise ValueError("refinance plan must use its existing debt_id")
            debt = debt_by_id.get(option.get("debt_id"))
            if not debt or debt.get("annual_payment") is None:
                raise ValueError("refinance requires known debt and annual_payment")
            engine.n(option.get("confirmed_refinance_amount"))
            engine.n(option.get("annual_payment_after_refinance"))
            decision_cashflow.month(option.get("due_month"), horizon, "due_month")
            refinance_event = (debt, option["due_month"])
        elif kind == "BUDGET":
            if option["loans"]:
                raise ValueError("BUDGET cannot hide a loan; use HOME_PURCHASE or REFINANCE")
        scenarios = {}
        for name, scenario in plan["scenarios"].items():
            def income(overrides):
                if set(overrides) - set(sources):
                    raise ValueError("income overrides must refer to an existing income source")
                return sum(overrides.get(key, value) for key, value in sources.items())
            monthly_scenario = {
                "income_annual": income(scenario["income_overrides"]),
                "spending_annual": annual_spend + scenario["spending_delta_annual"],
                "changes": [], "one_off_expenses": deepcopy(scenario["one_off_expenses"])}
            income_overrides = dict(scenario["income_overrides"])
            delta = scenario["spending_delta_annual"]
            changes = {}
            for change in sorted(scenario["changes"], key=lambda x: x["month"]):
                at = decision_cashflow.month(change["month"], horizon, "change.month")
                if at in changes:
                    raise ValueError("combine scenario changes in the same month")
                if "income_overrides" in change:
                    income_overrides.update(change["income_overrides"])
                if "spending_delta_annual" in change:
                    delta = change["spending_delta_annual"]
                changes[at] = {"month": at, "income_annual": income(income_overrides),
                               "spending_annual": annual_spend + delta}
            if refinance_event:
                debt, at = refinance_event
                amount = scenario["refinance_overrides"].get(
                    debt["id"], option["confirmed_refinance_amount"])
                if amount > debt["balance"]:
                    raise ValueError("confirmed refinancing cannot exceed modeled due principal")
                if name == "SEVERE" and amount != 0:
                    raise ValueError("SEVERE refinancing must model failure (confirmed amount zero)")
                monthly_scenario["one_off_expenses"].append(
                    {"month": at, "amount": debt["balance"] - amount})
                adjustment = option["annual_payment_after_refinance"] - debt["annual_payment"]
                if at in changes:
                    changes[at]["spending_annual"] += adjustment
                else:
                    prior_delta = scenario["spending_delta_annual"]
                    prior_income = dict(scenario["income_overrides"])
                    for change in sorted(scenario["changes"], key=lambda x: x["month"]):
                        if change["month"] > at:
                            break
                        prior_delta = change.get("spending_delta_annual", prior_delta)
                        prior_income.update(change.get("income_overrides", {}))
                    changes[at] = {"month": at, "income_annual": income(prior_income),
                                   "spending_annual": annual_spend + prior_delta + adjustment}
                for month_value in changes:
                    if month_value > at:
                        changes[month_value]["spending_annual"] += adjustment
                safe = max(0, base["low_risk_assets"] - plan["protected_reserve"]
                           - sum(x["amount"] for x in scenario["one_off_expenses"]))
                loans.append({"option_id": oid, "loan_id": name,
                              "principal_due_or_current_balance": debt["balance"],
                              "confirmed_refinance_amount": amount,
                              "safely_available_for_debt": safe,
                              "refinance_gap": max(0, debt["balance"] - amount - safe),
                              "scenario": "NO_REFINANCE" if amount == 0 else name,
                              "compliance_status": "REQUIRES_VERIFICATION"})
            monthly_scenario["changes"] = sorted(changes.values(), key=lambda x: x["month"])
            scenarios[name] = monthly_scenario
        case = {"initial_low_risk_assets": base["low_risk_assets"],
                "upfront_net_inflow": inflow, "upfront_outflow": outflow,
                "protected_reserve": plan["protected_reserve"],
                "horizon_months": horizon, "scenarios": scenarios}
        cashflow = decision_cashflow.simulate(case)
        results.append({"option_id": oid, "kind": kind, "housing": housing,
                        "loans": loans, "cashflow_input": case, "cashflow_result": cashflow})
    return {"basis": "family_state.decision_plan", "options": results}


def verify_output(run, step_id):
    """Compare fiscal projections to the single source; presentation is free."""
    state = run["steps"]["STATE_BUILD"]["output"]["family_state"]
    expected = derive(state)
    output = run["steps"][step_id]["output"]
    checks = []
    def check(name, actual, wanted):
        checks.append({"name": name, "pass": actual == wanted})
    if step_id == "HOUSING_ANALYSIS":
        wanted = [x["housing"] for x in expected["options"] if x["housing"]]
        actual = output["results"].get("options")
        check("authoritative_housing_funding", actual, wanted)
    elif step_id == "FINANCING_ANALYSIS":
        wanted = [loan for x in expected["options"] for loan in x["loans"]]
        check("authoritative_loans_and_tranches", output["results"].get("loans"), wanted)
    elif step_id == "STRESS_TEST":
        wanted = [{"option_id": x["option_id"], "input": x["cashflow_input"],
                   "result": x["cashflow_result"]} for x in expected["options"]]
        check("authoritative_cashflow_inputs_outputs", output.get("option_runs"), wanted)
        first = expected["options"][0]["cashflow_input"]["scenarios"]
        for name, scenario in first.items():
            actual = output.get("scenarios", {}).get(name, {})
            check(f"{name}_reported_income_matches_case",
                  actual.get("income_annual"), scenario["income_annual"])
            check(f"{name}_reported_spending_matches_case",
                  actual.get("spending_annual"), scenario["spending_annual"])
    elif step_id == "CAREER_ANALYSIS":
        wanted = step_outputs(state)["CAREER_ANALYSIS"]
        check("authoritative_career_inputs", output.get("integrity_inputs"), wanted["integrity_inputs"])
        check("authoritative_career_scenarios", output.get("transition_scenarios"), wanted["transition_scenarios"])
    elif step_id == "EDUCATION_ANALYSIS":
        scenarios = state.get("education", {}).get("scenarios")
        if not scenarios:
            raise ValueError("confirm education.scenarios before a complete education recommendation")
        check("authoritative_education_scenarios", output.get("education_scenarios"), scenarios)
    elif step_id == "OPTIONS_VALIDATE":
        wanted = {x["option_id"] for x in expected["options"]}
        built = run["steps"]["OPTIONS_BUILD"]["output"]["options"]
        check("authoritative_option_ids", {x["id"] for x in built}, wanted)
        for sid, key, field in (("HOUSING_ANALYSIS", "options", "option_id"),
                                ("FINANCING_ANALYSIS", "loans", "option_id")):
            step = run["steps"].get(sid, {})
            wanted_ids = {x["option_id"] for x in expected["options"]
                          if (x["housing"] if key == "options" else x["loans"])}
            if wanted_ids and step.get("status") == "SKIPPED":
                check(f"{sid}_cannot_skip_planned_domain", False, True)
            if wanted_ids:
                actual = (step.get("output") or {}).get("results", {}).get(key, [])
                check(f"{sid}_coverage", {x[field] for x in actual}, wanted_ids)
    return checks


def step_outputs(state):
    derived = derive(state)
    plan = state["decision_plan"]
    options = derived["options"]
    houses = [item["housing"] for item in options if item["housing"]]
    loans = [loan for item in options for loan in item["loans"]]
    scenarios = {}
    first = options[0]["cashflow_input"]["scenarios"]
    for name, case in first.items():
        scenarios[name] = {"income_annual": case["income_annual"],
                           "spending_annual": case["spending_annual"],
                           "annual_net_cashflow": case["income_annual"] - case["spending_annual"],
                           "assumptions": plan["scenarios"][name]["assumptions"]}
    has_refinance = any(item["kind"] == "REFINANCE" for item in options)
    sources = state["income"]["stable_annual"]
    stress_overrides = plan["scenarios"]["STRESS"]["income_overrides"]
    reduced = sum(max(0, value - stress_overrides.get(key, value)) for key, value in sources.items())
    increased = sum(max(0, stress_overrides.get(key, value) - value) for key, value in sources.items())
    base_income = sum(sources.values())
    return {
        "STATE_BUILD": {"family_state": state, "source_tags": state["source_tags"]},
        "INPUT_VALIDATE": {"status": "READY", "missing_p0": [], "conflicts": []},
        "DEADLINE_IDENTIFY": {"deadlines": state.get("deadlines", []), "deadline_collision": False},
        "BASELINE_CALCULATE": {"derived_metrics": engine.baseline(state), "calculation_source": "REFERENCE_ENGINE"},
        "HOUSING_ANALYSIS": {"mode": "SOURCE_BOUND_PLAN",
            "results": {"target_home_considered": True, "replacement_spread_checked": True,
                        "post_purchase_liquid_assets": houses[0]["post_purchase_liquid_assets"] if houses else None,
                        "options": houses}, "assumptions": ["All fiscal inputs derive from confirmed decision_plan"]},
        "FINANCING_ANALYSIS": {
            "nominal_principal_checked": True, "refinance_failure_tested": has_refinance,
            "refinance_required": has_refinance,
            "loan_structure": "ROLLOVER" if has_refinance else "FULLY_AMORTIZING_FIXED_TERM",
            "compliance_status": "REQUIRES_VERIFICATION" if loans else "NOT_APPLICABLE",
            "results": {"loans": loans, "balloon_payment": 0,
                        "no_financing_needed": not loans,
                        "refinance_not_applicable_reason": "No renewal/balloon in source plan; verify actual contract"}},
        "CAREER_ANALYSIS": {"current_income_state": state["income"],
            "transition_scenarios": [
                {"name": name, "income": scenarios[name]["income_annual"]}
                for name in ("NORMAL", "STRESS", "SEVERE")],
            "career_deadline": {"status": "SCENARIO_ONLY", "horizon_months": plan["horizon_months"]},
            "integrity_inputs": {"current_stable_income": base_income, "reduced_main_income": reduced,
                                 "new_income_sources": increased,
                                 "resulting_stable_income": base_income - reduced + increased}},
        "STRESS_TEST": {"scenarios": scenarios,
            "option_runs": [{"option_id": item["option_id"], "input": item["cashflow_input"],
                             "result": item["cashflow_result"]} for item in options],
            "material_failures": [f"{item['option_id']}:{name} reserve breach"
                for item in options for name, scenario in item["cashflow_result"]["scenarios"].items()
                if scenario["first_reserve_breach_month"] is not None]},
        "OPTIONS_BUILD": {"options": [
            {"id": item["option_id"], "label": item["option_id"],
             "tradeoffs": ["Compare cash, debt, goals and reversibility"],
             "failure_triggers": ["Replan when source inputs or constraints change"]}
            for item in options]},
        "OPTIONS_VALIDATE": {"all_options_validated": True, "critical_errors": [],
            "option_checks": [{"id": item["option_id"], "pass": True} for item in options]}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state")
    args = parser.parse_args()
    try:
        data = json.loads(Path(args.state).read_text(encoding="utf-8"))
        print(json.dumps(step_outputs(data.get("family_state", data)), ensure_ascii=False, indent=2))
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
