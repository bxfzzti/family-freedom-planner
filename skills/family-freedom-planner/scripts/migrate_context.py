#!/usr/bin/env python3
"""Migrate a legacy 0.9 context capsule to the explicit v1.4 envelope."""
import argparse
import json
from copy import deepcopy
from pathlib import Path

from validate_family_state import validate_state


def tag(as_of, source_type="USER_ESTIMATE", confidence="MEDIUM"):
    return {"source_type": source_type, "as_of": as_of, "confidence": confidence}


def migrate(old):
    if not isinstance(old, dict) or old.get("schema_version") != "0.9":
        raise ValueError("expected a legacy schema_version 0.9 context")
    for key in ("income", "expenses", "assets", "housing", "household",
                "career", "education", "preferences", "debts"):
        if key in old and not isinstance(old[key], dict):
            raise ValueError(f"legacy {key} must be an object; original file is unchanged")
    for key in ("goals", "assumptions", "open_questions", "decision_journal", "deadlines"):
        if key in old and not isinstance(old[key], list):
            raise ValueError(f"legacy {key} must be a list; original file is unchanged")
    as_of = old.get("as_of")
    income = old.get("income", {})
    expenses = old.get("expenses", {})
    assets = old.get("assets", {})
    housing = old.get("housing", {})
    reported_income = income.get("stable_household_income_annual")
    reported_financial = assets.get("cash_and_financial_assets")
    home_value = housing.get("primary_home_value")
    home_debt = housing.get("primary_home_debt")
    state = {
        "schema_version": "1.4.0", "as_of": as_of,
        "currency": "CNY", "amount_unit": "yuan",
        "income": {
            "period": "annual", "tax_basis": "UNKNOWN",
            "stable_annual": {"household_reported": reported_income},
            "high_risk_annual": income.get("high_risk_income_annual")},
        "expenses": {
            "period": "annual",
            "annual_total": expenses.get("annual_household_spend"),
            "annual_mandatory": None,
            "annual_total_includes_debt_payments": None},
        "assets": {
            "cash": None, "low_risk_investments": None, "investments": None,
            "other_liquid": None,
            "unallocated_financial_assets": reported_financial,
            "real_estate": ([{
                "id": "primary_home", "market_value": home_value,
                "linked_debt_id": "primary_home_debt" if home_debt is not None else None,
                "linked_debt_balance": home_debt,
                "sellable_for_plan": None}] if home_value is not None else []),
            "other_non_liquid": None},
        "debts": {"items": ([{
            "id": "primary_home_debt", "balance": home_debt,
            "balance_basis": "CURRENT_BALANCE"}] if home_debt is not None else [])},
        "household": old.get("household", {}),
        "career": old.get("career", {}),
        "education": old.get("education", {}),
        "housing": {key: value for key, value in housing.items()
                    if key not in ("primary_home_value", "primary_home_debt")},
        "preferences": old.get("preferences", {}),
        "deadlines": old.get("deadlines", []),
        "primary_decision": old.get("primary_decision"),
        "source_tags": {}
    }
    unresolved = []
    # Retain explicit component amounts; never turn a combined figure into cash.
    components = ("cash", "low_risk_investments", "investments", "other_liquid")
    for key in components:
        value = assets.get(key)
        if type(value) in (int, float) and value >= 0:
            state["assets"][key] = value
    known = sum(value for key in components
                if type(value := state["assets"][key]) in (int, float))
    if type(reported_financial) in (int, float):
        if reported_financial >= known:
            state["assets"]["unallocated_financial_assets"] = reported_financial - known
        else:
            state["assets"]["unallocated_financial_assets"] = None
            unresolved.append("legacy financial total is less than its reported components")
    if type(assets.get("other_non_liquid")) in (int, float):
        state["assets"]["other_non_liquid"] = assets["other_non_liquid"]
    legacy_debts = old.get("debts", {}).get("items", []) if isinstance(old.get("debts", {}), dict) else []
    if not isinstance(legacy_debts, list):
        unresolved.append("legacy debts.items is not a list; original is retained")
        legacy_debts = []
    for index, item in enumerate(legacy_debts):
        if not isinstance(item, dict):
            unresolved.append(f"legacy debt {index} requires mapping")
            continue
        mapped = deepcopy(item)
        mapped["id"] = item.get("id") if isinstance(item.get("id"), str) and item["id"] else f"legacy_debt_{index}"
        mapped["balance"] = item.get("balance") if type(item.get("balance")) in (int, float) else None
        mapped["balance_basis"] = item.get("balance_basis", "UNKNOWN")
        if mapped["id"] == "primary_home_debt":
            primary = next((x for x in state["debts"]["items"] if x["id"] == mapped["id"]), None)
            if primary and primary["balance"] == mapped["balance"]:
                continue
            mapped["id"] = f"legacy_debt_{index}"
            unresolved.append("conflicting primary-home debt retained under a separate id")
        if any(x["id"] == mapped["id"] for x in state["debts"]["items"]):
            mapped["id"] = f"legacy_debt_{index}"
            unresolved.append("duplicate legacy debt id requires confirmation")
        state["debts"]["items"].append(mapped)
    if legacy_debts:
        unresolved.append("confirm all migrated debts and whether a listed debt duplicates primary-home debt")
    for group in ("assets", "income", "expenses"):
        allowed = {
            "assets": set(components) | {"cash_and_financial_assets", "other_non_liquid"},
            "income": {"stable_household_income_annual", "high_risk_income_annual", "high_income_deadline"},
            "expenses": {"annual_household_spend"}}[group]
        unknown = set(old.get(group, {})) - allowed
        if unknown:
            unresolved.append(f"unmapped legacy {group} fields retained: {', '.join(sorted(unknown))}")
    paths = {
        "income.stable_annual.household_reported": reported_income,
        "income.high_risk_annual": income.get("high_risk_income_annual"),
        "expenses.annual_total": expenses.get("annual_household_spend"),
        "assets.unallocated_financial_assets": reported_financial,
        "assets.real_estate.0.market_value": home_value,
        "assets.real_estate.0.linked_debt_balance": home_debt,
        "debts.items.0.balance": home_debt,
    }
    for key in components + ("other_non_liquid",):
        paths[f"assets.{key}"] = state["assets"][key]
    paths["assets.unallocated_financial_assets"] = state["assets"]["unallocated_financial_assets"]
    for index, item in enumerate(state["debts"]["items"]):
        paths[f"debts.items.{index}.balance"] = item["balance"]
        if item.get("annual_payment") is not None:
            paths[f"debts.items.{index}.annual_payment"] = item["annual_payment"]
    state["source_tags"] = {path: tag(as_of, "MODEL_ASSUMPTION", "LOW") for path, value in paths.items()
                            if value is not None}
    result = {
        "schema_version": "1.4.0", "as_of": as_of, "family_state": state,
        "goals": old.get("goals", []),
        "assumptions": list(old.get("assumptions", [])),
        "open_questions": list(old.get("open_questions", [])),
        "decision_journal": old.get("decision_journal", [])
    }
    result["open_questions"].extend([
        "确认家庭收入是税前还是税后，并拆分稳定收入来源",
        "把合并金融资产拆分为现金、低风险资产、波动资产和其他流动资产",
        "确认年支出是否包含全部债务还款，并填写必要支出"])
    result["open_questions"].extend(unresolved)
    check = validate_state(state, calculation_ready=False)
    if check["status"] != "PASS":
        raise ValueError("migration produced invalid state: " + "; ".join(check["errors"]))
    result["migration"] = {
        "from": "0.9", "to": "1.4.0", "calculation_ready": False,
        "reason": "legacy tax, spending and financial-asset composition are not explicit",
        "original_context": deepcopy(old), "unresolved_fields": unresolved,
        "resolved": False}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("legacy_context")
    args = parser.parse_args()
    try:
        result = migrate(json.loads(Path(args.legacy_context).read_text(encoding="utf-8")))
        encoded = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
    except (ValueError, TypeError, OSError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(2)
    print(encoded)


if __name__ == "__main__":
    main()
